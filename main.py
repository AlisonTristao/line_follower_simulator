from simulator import *
import pandas as pd
import cvxpy as cp

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
track_length        = 0.02 # meters
sensor_spacing      = 0.008 # meters

# future points
future_points       = 45   # number of future points
future_spacing      = 3    # resolutuin of the track

# setup the simulation
start_simulation(screen_size, screen_fps, seed=track_seed, track_type=track_type, track_length=track_length, sensor_spacing=sensor_spacing)

# setup the car dynamics
set_car_dynamics(wheels_radius, wheels_distance, wheels_RPM, ke_l, ke_r, accommodation_time_l, accommodation_time_r, sensor_distance, sensor_count)

# setup the future points
set_future_points(future_points, future_spacing)

def make_step(alpha, len):
    # --- make step ---
    step = []
    for i in range(len):
        step.append(alpha)
    return step

def matriz_por_indices(caminho_csv, indices_colunas, limit=-1):
    try:
        df = pd.read_csv(caminho_csv, header=None)
        if max(indices_colunas) >= len(df.columns):
            raise IndexError("Um dos índices fornecidos excede o número de colunas no CSV.")
        # stop on limit
        return df.iloc[:, indices_colunas].values[:limit].tolist()
    except Exception as e:
        print(f"Erro ao processar o CSV: {e}")
        return []

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

# --- insert your code here --- #

alpha_l = math.exp(-z*5/accommodation_time_l)
alpha_r = math.exp(-z*5/accommodation_time_r)
beta_l = ke_l - alpha_l
beta_r = ke_r - alpha_r

print("alpha_l: ", round(alpha_l, 5))
print("alpha_r: ", round(alpha_r, 5))
print("beta_l: ", round(beta_l, 3))
print("beta_r: ", round(beta_r, 3))

N_horizon = future_points #int(math.log(0.01)/math.log(max(alpha_l, alpha_r)))
N_ul = 5
N_ur = 5

lamb_l = 1e-3   /N_ul
lamb_r = 1e-3   /N_ur
epsl_d = 1      /N_horizon
epsl_a = 5e-1   /N_horizon

v1 = 0
v2 = 0

delta_u_l = 0
delta_u_r = 0

order = 3
free_l = matriz_por_indices("car_modeling/coeffs.csv", [0, 1, 2], N_horizon)
free_r = matriz_por_indices("car_modeling/coeffs.csv", [3, 4, 5], N_horizon)
last_theta_l = [0, 0, 0]
last_theta_r = [0, 0, 0]

# --- matrizes do controle --- #

R_l = np.eye(N_ul) * lamb_l
R_r = np.eye(N_ur) * lamb_r
R = np.block([
    [R_l, np.zeros((N_ur, N_ul))],
    [np.zeros((N_ul, N_ur)), R_r]
])

Q_v = np.eye(N_horizon) * epsl_d
Q_w = np.eye(N_horizon) * epsl_a
Q = np.block([
    [Q_w, np.zeros((N_horizon, N_horizon))],
    [np.zeros((N_horizon, N_horizon)), Q_v]
])

g_l = matriz_por_indices("car_modeling/g.csv", [0])
g_r = matriz_por_indices("car_modeling/g.csv", [1])

G_lw = matrix_G_array(g_l, N_ul, N_horizon) * -wheels_radius/(2*wheels_distance)
G_lv = matrix_G_array(g_l, N_ul, N_horizon) * wheels_radius/4
G_rw = matrix_G_array(g_r, N_ur, N_horizon) * wheels_radius/(2*wheels_distance)
G_rv = matrix_G_array(g_r, N_ur, N_horizon) * wheels_radius/4

G = np.block([
    [G_lw, G_rw], 
    [G_lv, G_rv]
])

# solution of quadratic problem
#K = np.linalg.inv(G.T @ Q @ G + R) @ G.T @ Q
#K1 = K[0]

delta_u = cp.Variable(N_ul + N_ur)

H = 2 * (G.T @ Q @ G + R)

delta_u_max = 1
delta_u_min = -1
u_max = 100
u_min = -100

while True:
    # saturate the inputs
    v1 += delta_u_l
    v2 += delta_u_r

    v1 = max(min(v1, u_max), u_min)
    v2 = max(min(v2, u_max), u_min)

    # --- step the simulation, future_points, speed, omega here --- #

    data = step_simulation(v1, v2)
    if data is None: 
        break
    else:
        line, future_points, speed, theta, omega_wheels = data

    # --- integrate the omega signal --- #

    last_theta_l.append(last_theta_l[-1] + omega_wheels[0] * z)
    last_theta_r.append(last_theta_r[-1] + omega_wheels[1] * z)
    if len(last_theta_l) > 3:
        last_theta_l.pop(0)
        last_theta_r.pop(0)

    # --- calculate the free future response --- #

    free_future_l = free_GPC(free_l, last_theta_l.copy())
    free_future_r = free_GPC(free_r, last_theta_r.copy())

    future_distance = []
    future_theta = []

    # --- calculate the current theta and distance --- #

    current_theta = (last_theta_l[-1] - last_theta_r[-1]) * wheels_radius/wheels_distance
    current_distance = (last_theta_l[-1] + last_theta_r[-1]) * wheels_radius/2

    for i in range(len(free_future_l)):
        future_distance.append((free_future_l[i] + free_future_r[i]) * wheels_radius/2)
        future_theta.append((free_future_l[i] - free_future_r[i]) * wheels_radius/wheels_distance)

    future_theta = np.array(future_theta)
    future_distance = np.array(future_distance)

    # --- convert to delta --- #

    future_theta = future_theta - current_theta
    future_distance = future_distance - current_distance

    # --- reference using linearization --- #

    x = [future_points[i][0] for i in range(len(future_points))]
    y = [future_points[i][1] for i in range(len(future_points))]

    d0 = 0.3
    angle = np.array(x)/d0
    distance = np.array(y)

    # --- error of reference --- #

    erro_theta = -angle + future_theta
    erro_distance = distance - future_distance

    erro = np.concatenate((erro_theta, erro_distance), axis=0)

    # --- optimal control --- #

    # define the quadratic problem
    c = 2 * -(G.T @ Q @ erro)
    cost = 0.5 * (delta_u.T @ H @ delta_u) + c.T @ delta_u
    
    constraints = [
        # delta u limit
        delta_u <= delta_u_max,
        delta_u >= delta_u_min,
        # u limit
        cp.sum(delta_u[:N_ul]) + v1 <= u_max,
        cp.sum(delta_u[:N_ul]) + v2 >= u_min,
        cp.sum(delta_u[N_ul:]) + v1 <= u_max,
        cp.sum(delta_u[N_ul:]) + v2 >= u_min,
    ]

    prob = cp.Problem(cp.Minimize(cost), constraints)

    prob.solve(solver=cp.OSQP)

    delta_u_l = delta_u.value[0]
    delta_u_r = delta_u.value[N_ul]

    # --- update the graphs --- #

    set_graph_reference(angle * 30, distance * 30)
    set_graph_free_response(future_theta * 30, future_distance * 30)
    set_graph_error(erro_theta, erro_distance)
    set_graph_future_control(delta_u[:N_ul] * 30, delta_u[N_ul:] * 30)