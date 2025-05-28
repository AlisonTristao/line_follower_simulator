from simulator import *
import pandas as pd

# screen settings => sizes FULL, MEDIUM, SMALL
screen_size = MEDIUM
screen_fps = 80
z = 1/screen_fps
track_seed = 1112

# car constants
wheels_radius       = 0.04  # meters
wheels_distance     = 0.15  # meters
wheels_RPM          = 1000  # RPM
sensor_distance     = wheels_distance  # meters
sensor_count        = 15    
sensor_spacing      = 0.008 # meters

# motor constants
ke_l = 1.00
ke_r = 1.00
accommodation_time_l = 0.62 # seconds
accommodation_time_r = 0.58 # seconds

# track caracteristics
track_type          = LEMNISCATE
track_length        = 0.02 # metersref_theta
sensor_spacing      = 0.008 # meters

# future points
future_points       = 40    # number of future points
future_spacing      = 10    # resolutuin of the track

# setup the simulation
start_simulation(screen_size, screen_fps, seed=track_seed, track_type=track_type, track_length=track_length, sensor_spacing=sensor_spacing)

# setup the car dynamics
set_car_dynamics(wheels_radius, wheels_distance, wheels_RPM, ke_l, ke_r, accommodation_time_l, accommodation_time_r, sensor_distance, sensor_count)

# setup the future points
set_future_points(future_points, future_spacing)

def make_ramp(alpha, len):
    # --- make ramp ---
    ramp = []
    for i in range(len):
        ramp.append(i * alpha)
    return ramp

def make_step(alpha, len):
    # --- make step ---
    step = []
    for i in range(len):
        step.append(alpha)
    return step

def angle_between_vectors(v1, v2):
    # Produto vetorial (em 2D é um escalar)
    det = v1[0] * v2[1] - v1[1] * v2[0]
    # Produto escalar
    dot = v1[0] * v2[0] + v1[1] * v2[1]
    return math.atan2(det, dot)

def converte_array(array):
    angle_list = []
    distance_list = []
    total_angle = 0
    total_distance = 0

    for i in range(1, len(array)):
        p0 = array[i - 1]
        p1 = array[i]
        v1 = np.subtract(p1, p0)
        dist = np.linalg.norm(v1)
        total_distance += dist
        distance_list.append(total_distance)

        if i == 1:
            angle_list.append(0)  # sem ângulo no primeiro segmento
            continue

        p_1 = array[i - 2]
        v0 = np.subtract(p0, p_1)

        angle = angle_between_vectors(v0, v1)
        total_angle += angle
        angle_list.append(total_angle)

    return np.array(angle_list), np.array(distance_list)

def converte_xy_to_theta(x, y):
    return math.atan2(x, y)

def calculates_hipotenusa(x, y):
    return math.sqrt(x**2 + y**2)

def matriz_por_indices(caminho_csv, indices_colunas):
    try:
        df = pd.read_csv(caminho_csv, header=None)
        if max(indices_colunas) >= len(df.columns):
            raise IndexError("Um dos índices fornecidos excede o número de colunas no CSV.")
        return df.iloc[:, indices_colunas].values.tolist()
    except Exception as e:
        print(f"Erro ao processar o CSV: {e}")
        return []

def rotate_point(x, y, angle):
    # Rotaciona o vetor (x, y) pelo ângulo dado (em radianos)
    cos_a = math.cos(-angle)  # sinal negativo para rotacionar sistema de coordenadas
    sin_a = math.sin(-angle)
    x_rot = x * cos_a - y * sin_a
    y_rot = x * sin_a + y * cos_a
    return x_rot, y_rot

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

def matrix_G_array(array_g, N_u, N):
    # --- matriz de convolução ---
    G = np.zeros((len(array_g), len(array_g)))
    for i in range(len(array_g)):
        for j in range(len(array_g)):
            if j <= i:
                G[i][j] = array_g[i-j][0]

    # return just the N_u first columns and N rows
    G = G[:N, :N_u]
    return G

def free_GPC(free_matrix, last_y):
    if len(free_matrix[0]) != len(last_y):
        print("coeffs diferentes dos y passados!")
        return
    
    last_y = last_y[::-1]
    future = []
    for alpha in free_matrix:
        y_k = sum([alpha[i] * last_y[i] for i in range(len(alpha))])
        future.append(y_k)
    
    return future

def make_interp(array, len_):
    x_original = np.linspace(0, 1, len(array))  # Posições originais
    x_interp = np.linspace(0, 1, len_)  # Posições desejadas
    array_result = np.interp(x_interp, x_original, array)  # Interpolação linear
    
    return array_result

# --- insert your code here --- #

alpha_l = math.exp(-z*5/accommodation_time_l)
alpha_r = math.exp(-z*5/accommodation_time_r)
beta_l = ke_l - alpha_l
beta_r = ke_r - alpha_r

print("alpha_l: ", round(alpha_l, 5))
print("alpha_r: ", round(alpha_r, 5))
print("beta_l: ", round(beta_l, 3))
print("beta_r: ", round(beta_r, 3))

N_horizon = 40 #int(math.log(0.01)/math.log(max(alpha_l, alpha_r)))
N_uw = N_horizon
N_uv = N_horizon

lamb_v = 0.01
lamb_w = 0.01
epsl_v = 0.001
epsl_w = 1

v1 = 1
v2 = 1

delta_u_l = 0
delta_u_r = 0

order = 3
free_l = matriz_por_indices("car_modeling/coeffs.csv", [0, 1, 2])
free_r = matriz_por_indices("car_modeling/coeffs.csv", [3, 4, 5])
last_theta_l = [0, 0, 0]
last_theta_r = [0, 0, 0]

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

g_l = matriz_por_indices("car_modeling/g.csv", [0])
g_r = matriz_por_indices("car_modeling/g.csv", [1])

G_lw = matrix_G_array(g_l, N_uw, N_horizon) * -wheels_radius/wheels_distance
G_lv = matrix_G_array(g_l, N_uv, N_horizon) * wheels_radius/2
G_rw = matrix_G_array(g_r, N_uw, N_horizon) * wheels_radius/wheels_distance
G_rv = matrix_G_array(g_r, N_uv, N_horizon) * wheels_radius/2

G = np.block([
    [G_lw, G_lv], 
    [G_rw, G_rv]
])

# solution of quadratic problem
K = np.linalg.inv(G.T @ Q @ G + R) @ G.T @ Q
K1 = K[0]

while True:
    # saturate the inputs
    v1 += delta_u_l
    v2 += delta_u_r

    v1 = max(min(v1, 100), -100)
    v2 = max(min(v2, 100), -100)

    # --- step the simulaine, future_points, speed, omega tion here --- #

    data = step_simulation(v1, v2)
    if data is None: 
        break
    else:
        line, future_points, speed, omega, omega_wheels = data

    # --- calculate free response --- #
    last_theta_l.append(last_theta_l[-1] + omega_wheels[0] * z)
    last_theta_r.append(last_theta_r[-1] + omega_wheels[1] * z)
    if len(last_theta_l) > 3:
        '''value_l = last_theta_l[0]
        value_r = last_theta_r[0]
        for i in range(3):
            last_theta_l[i] -= value_l
            last_theta_r[i] -= value_r'''
        last_theta_l.pop(0)
        last_theta_r.pop(0)

    #angle, distante = converte_array(future_points)

    free_future_l = free_GPC(free_l, last_theta_l.copy())
    free_future_r = free_GPC(free_r, last_theta_r.copy())

    future_distance = []
    future_theta = []

    for i in range(len(free_future_l)):
        future_distance.append((free_future_l[i] + free_future_r[i]) * wheels_radius/2)
        future_theta.append((free_future_l[i] - free_future_r[i]) * wheels_radius/wheels_distance)

    #print("left", free_future_l[0], last_theta_l[-1], "right", free_future_r[0], last_theta_r[-1])
    #print(last_theta_l[-1], last_theta_r[-1])
    #print("dist", future_distance[1], speed)
    print("theta", future_theta[0], omega)
    #print("distance", future_distance)
    #print("angle", future_theta)

    angle = make_step(3.14159, N_horizon)
    distante = make_step(0.01, N_horizon)

    #print(future_points)
    #angle, distante = converte_array(future_points)
    #print("angle", angle)
    #print("distante", distante)

    set_graph_reference(angle, distante)
    set_graph_free_response(future_theta, future_distance)

    angle = np.array(angle)
    distante = np.array(distante)
    future_theta = np.array(future_theta)
    future_distance = np.array(future_distance)

    erro_theta = angle - future_theta
    erro_distante = distante - future_distance

    erro = np.concatenate((erro_theta, erro_distante), axis=0)

    delta_u = K @ erro
    delta_u_r = delta_u[0]
    delta_u_l = delta_u[N_uw]
