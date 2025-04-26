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

def converte_xy_to_theta(x, y):
    return math.atan2(x, y)

def converte_array(array):
    # array de diferenças
    #diff = np.diff(array, axis=0)
    theta = []
    for i in range(len(array)):
        theta.append(converte_xy_to_theta(array[i][0], array[i][1]) * points_s_w)
    
    # calcula a hipotenusa
    hipotenusa = []
    for i in range(len(array)):
        hipotenusa.append(calculates_hipotenusa(array[i][0], array[i][1]) * points_s_v)

    return np.array(theta), np.array(hipotenusa)

def resp_degrau(alpha, k):
    return (1 - alpha**k)

def matrix_G(N, alpha=0.8):
    # --- matriz de convolução ---
    G = np.zeros((N, N))
    for i in range(N):
        for j in range(N):
            if j <= i:
                G[i][j] = resp_degrau(alpha, i-j + 1)
    return G

def calculates_hipotenusa(x, y):
    return math.sqrt(x**2 + y**2)

def calculate_free(free, alpha, largura, delta_u, ke):
    free = np.roll(free, -1)  # Desloca os valores para a esquerda
    free[-1] = free[-2]  # Mantém o último valor igual ao penúltimo

    for i in range(largura):
        free[i] = (delta_u * (1-alpha**(i+1)) * ke) + free[i]
    
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

# --- insert your code here --- #

v_max = wheels_RPM/60 * 2 * math.pi * wheels_radius
w_max = 2*v_max/wheels_distance

speed_med = 0

ke_v = 4.19/100
ke_w = w_max/100
print(ke_v * 100)

points_s_w = ke_w/0.05
points_s_v = ke_v/0.003

v1 = speed_med
v2 = speed_med

delta_u_w = 0
delta_u_v = 0

alpha = 0.9
largura = int(math.log(0.01)/math.log(alpha))

free_w = np.array([0] * (largura + 1), dtype=float)
free_v = np.array([0] * (largura + 1), dtype=float)

lamb_v = 10.0
lamb_w = 0.01

Q_w = np.eye(largura) * ke_w**2 * lamb_w
Q_v = np.eye(largura) * ke_v**2 * lamb_v

G = matrix_G(largura, alpha)
K_W = np.linalg.inv(G.T @ G + Q_w) @ G.T
K1_W = K_W[0, :]

K_V = np.linalg.inv(G.T @ G + Q_v) @ G.T
K1_V = K_V[0, :]

while True:
    #print("u=", u)
    v1 += delta_u_v + delta_u_w
    v2 += delta_u_v - delta_u_w

    # --- step the simulaine, future_points, speed, omega tion here --- #
    data = step_simulation(v1, v2)
    if data is None: 
        break
    else:
        line, future_points, speed, omega = data

    # --- calculate free response --- #

    free_w = calculate_free(free_w, alpha, largura + 1, delta_u_w, ke_w)
    free_v = calculate_free(free_v, alpha, largura + 1, delta_u_v, ke_v)

    # --- calculate the reference trajectory --- #

    ref_theta, ref_vm = converte_array(future_points)
    
    r_w = make_interp(ref_theta, largura)
    r_v = make_interp(ref_vm, largura)

    # --- calculate the model error --- #

    eta_w = (omega - free_w[0])
    eta_v = (speed - free_v[0])

    # --- calculate the control action --- #

    erro_v = r_v - (free_v[1:61] + eta_v)
    delta_u_v = K1_V @ erro_v

    erro_w = r_w - (free_w[1:61] + eta_w)
    delta_u_w = K1_W @ erro_w