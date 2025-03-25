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
future_points       = 10    # number of future points
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
        theta.append(converte_xy_to_theta(array[i][0], array[i][1]) * points_s)
    
    # calcula a hipotenusa
    hipotenusa = []
    for i in range(len(array)):
        hipotenusa.append(calculates_hipotenusa(array[i][0], array[i][1]))

    return theta, hipotenusa

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

def calculate_free(free, alpha, largura, delta_u):
    free = np.roll(free, -1)  # Desloca os valores para a esquerda
    free[-1] = free[-2]  # Mantém o último valor igual ao penúltimo

    for i in range(largura):
        free[i] = (delta_u * (1-alpha**i) * ke_w) + free[i]
    
    return free  # Retorna o array atualizado

# --- insert your code here --- #

# ---
v_max = wheels_RPM/60 * 2 * math.pi * wheels_radius
w_max = 2*v_max/wheels_distance

speed_med = 70

ke_v = 4.19/100
ke_w = w_max/100

points_s = ke_w/0.1

v1 = speed_med
v2 = speed_med

delta_u = 0

alpha = 0.94
largura = int(math.log(0.01)/math.log(alpha))
free = np.array([0] * largura, dtype=float)
# ---

G = matrix_G(10, alpha)
K = np.linalg.inv(G.T @ G + 1.2 * np.eye(10)) @ G.T
K1 = K[0, :]

counter = 0
while True:
    #print("u=", u)
    v1 -= delta_u
    v2 += delta_u

    # --- step the simulaine, future_points, speed, omega tion here --- #
    data = step_simulation(v1, v2)
    if data is None: 
        break
    else:
        line, future_points, speed, omega = data

    free = calculate_free(free, alpha, largura, delta_u)
    ref_theta, ref_vm = converte_array(future_points)
    ref_theta = np.array(ref_theta)

    const = 0 #(-omega + free[0])
    erro = ref_theta - (free[0:10] + const)
    result = K1 @ erro
    delta_u = result

    counter += 1