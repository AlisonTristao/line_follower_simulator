from simulator import *
from control import Control
import matplotlib.pyplot as plt

# screen settings => sizes FULL, MEDIUM, SMALL
screen_size = MEDIUM
screen_fps = 80
track_seed = 1111

# car constants
wheels_radius       = 0.04  # meters
wheels_distance     = 0.15  # meters
wheels_RPM          = 1000  # RPM
sensor_distance     = wheels_distance  # meters
sensor_count        = 15    

# motor constants
ke                  = 1.0 # static gain of V1 => (y = ke * v)
accommodation_time  = 1.0 # seconds

# track caracteristics
track_type          = CIRCLE
track_length        = 0.015 # metersref_theta
sensor_spacing      = 0.008 # meters

# future points
future_points       = 6    # number of future points
future_spacing      = 40    # resolutuin of the track

# setup the simulation
start_simulation(screen_size, screen_fps, seed=track_seed, track_type=track_type, track_length=track_length, sensor_spacing=sensor_spacing)

# setup the car dynamics
set_car_dynamics(wheels_radius, wheels_distance, wheels_RPM, ke, accommodation_time, sensor_distance, sensor_count)

# setup the future points
set_future_points(future_points, future_spacing)

def converte_array(array):
    # array de diferenças
    #diff = np.diff(array, axis=0)
    theta = []
    for i in range(len(array)):
        theta.append(converte_xy_to_theta(array[i][0], array[i][1]) * points_s_w)
    
    # calcula a hipotenusa
    hipotenusa = []
    for i in range(len(array)):
        delta_x = array[i][0] - array[i-1][0] if i > 0 else array[i][0]
        delta_y = array[i][1] - array[i-1][1] if i > 0 else array[i][1]

        hipotenusa.append(calculates_hipotenusa(delta_x, delta_y) * points_s_v)

    return np.array(theta), np.array(hipotenusa)

def converte_xy_to_theta(x, y):
    return math.atan2(x, y)

def calculates_hipotenusa(x, y):
    return math.sqrt(x**2 + y**2)

def resp_degrau(alpha, k):
    return (1 - alpha**k)

def matrix_G(N, N_u, alpha=0.8, beta=0.2):
    # --- matriz de convolução ---
    G = np.zeros((N, N))
    for i in range(N):
        for j in range(N):
            if j <= i:
                G[i][j] = resp_degrau(alpha, i-j + 1) * beta/(1 - alpha)
    # return just the N_u first columns
    G = G[:, :N_u]
    return G

def calculate_free(free, alpha, beta, N_horizon, delta_u, ke):
    free = np.roll(free, -1)  # Desloca os valores para a esquerda
    free[-1] = free[-2]  # Mantém o último valor igual ao penúltimo

    for i in range(N_horizon):
        free[i] = (delta_u * (1-alpha**(i+1)) * (beta/(1 - alpha)) * ke) + free[i]
    
    return free  # Retorna o array atualizado

def make_step(array, len_):
    array_result = np.zeros(len_)
    qtd = len_//len(array)
    for i in range(len_):
        array_result[i] = array[i//qtd]

    return array_result

def make_interp(array, len_):
    x_original = np.linspace(0, 1, len(array))  # Posições originais
    x_interp = np.linspace(0, 1, len_)  # Posições desejadas
    array_result = np.interp(x_interp, x_original, array)  # Interpolação linear
    
    return array_result

def pad_to_shape(matrix, target_shape):
    padded = np.zeros(target_shape)
    rows, cols = matrix.shape
    padded[:rows, :cols] = matrix
    return padded

# --- insert your code here --- #

v_max = wheels_RPM/60 * 2 * math.pi * wheels_radius
w_max = 2*v_max/wheels_distance

ke_v = v_max/100
ke_w = w_max/100

points_s_w = ke_w/0.065
points_s_v = ke_v/0.0035

# --- setup the control --- #

alpha_l = 0.8
alpha_r = 0.9
beta_l = 0.98 - alpha_l
beta_r = 1 - alpha_r

N_horizon = int(math.log(0.01)/math.log(max(alpha_l, alpha_r)))
N_uw = 5
N_uv = 5

lamb_v = 0.015
lamb_w = 0.01
epsl_v = 0.003
epsl_w = 1

v1 = 0
v2 = 0

delta_u_l = 0
delta_u_r = 0

free_l = np.zeros(N_horizon)
free_r = np.zeros(N_horizon)

# --- matrizes do controle --- #

R_v = np.eye(N_uv) * lamb_v
R_w = np.eye(N_uw) * lamb_w
R = np.block([
    [R_w, np.zeros((N_uw, N_uv))],
    [np.zeros((N_uv, N_uw)), R_v]
])

Q_v = np.eye(N_horizon) * epsl_v
Q_w = np.eye(N_horizon) * epsl_w
Q = np.block([
    [Q_w, np.zeros((N_horizon, N_horizon))],
    [np.zeros((N_horizon, N_horizon)), Q_v]
])

G_lw = matrix_G(N_horizon, N_uw, alpha_l, beta_l) * ke_w
G_rw = matrix_G(N_horizon, N_uw, alpha_r, beta_r) * -ke_w
G_lv = matrix_G(N_horizon, N_uv, alpha_l, beta_l) * ke_v
G_rv = matrix_G(N_horizon, N_uv, alpha_r, beta_r) * ke_v
G = np.block([
    [G_lw, G_lv], 
    [G_rw, G_rv]
])

# solution of quadratic problem
K = np.linalg.inv(G.T @ Q @ G + R) @ G.T @ Q
K1 = K[0]

while True:
    v1 += delta_u_l
    v2 += delta_u_r

    # --- step the simulaine, future_points, speed, omega tion here --- #

    data = step_simulation(v1, v2)
    if data is None: 
        break
    else:
        line, future_points, speed, omega = data

    # --- calculate free response --- #

    free_l = calculate_free(free_l, alpha_l, beta_l, N_horizon, delta_u_l, 1)
    free_r = calculate_free(free_r, alpha_r, beta_r, N_horizon, delta_u_r, 1)
    free_w = (free_l - free_r) * ke_w/2
    free_v = (free_l + free_r) * ke_v/2

    eta_w = (omega - free_w[0])
    eta_v = (speed - free_v[0])

    free = np.concatenate((free_w + eta_w, free_v + eta_v), axis=0)

    # --- calculate the reference trajectory --- #

    ref_theta, ref_vm = converte_array(future_points)

    r_w = make_interp(ref_theta, N_horizon)
    r_v = make_interp(ref_vm, N_horizon)

    ref = np.concatenate((r_w, r_v), axis=0)

    # --- calculate the control action --- #

    erro = (ref - free)
    delta_u = K @ erro
    delta_u_l = delta_u[0]
    delta_u_r = delta_u[N_uw]