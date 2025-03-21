from simulator import *

# car constants
wheels_radius       = 0.04  # meters
wheels_distance     = 0.10  # meters
wheels_RPM          = 1000  # RPM
sensor_distance     = 0.10  # meters
sensor_count        = 15    

# track caracteristics
track_type          = CIRCLE
track_length        = 0.015 # meters
sensor_spacing      = 0.008 # meters

# motor constants
ke                  = 1.0 # static gain of V1 => (y = ke * v)
accommodation_time  = 1.0 # seconds

# setup the simulation
start_simulation(fps=80, seed=1111, track_type=track_type, track_length=track_length, sensor_spacing=sensor_spacing)

# setup the car dynamics
set_car_dynamics(wheels_radius, wheels_distance, wheels_RPM, ke, accommodation_time, sensor_distance, sensor_count)

# --- insert your code here --- #
v1 = 0
v2 = 0

# example for calculating the position of the line
last_mediam = 0
def calculate_postion(line):
    global last_mediam
    sum = 0
    pesos = 0
    for i in range(len(line)):
        sum += line[i] * (i+1)
        pesos += line[i]

    if pesos < 0.3:
        mediam = last_mediam
    else:
        mediam = sum/pesos
        last_mediam = mediam

    return mediam - len(line)/2

sample_time = 1/80
u = 0
kp = 0.3
ki = 0.3
kd = 0.1
last_error = 0
integral = 0

# example for calculating the control
def pid_control(error):
    global last_error, integral, kp, ki, kd, sample_time
    error = calculate_postion(line)
    integral += error * sample_time
    derivada = (error - last_error)/sample_time    

    delta_u = kp * error + kd * derivada + ki * integral 
    last_error = error
    return delta_u

for i in range(int(1/sample_time)):
    line = step_simulation(v1, v2)

while True:
    # --- step the simulation here --- #
    line = step_simulation(v1, v2)
    if line is None:
        break

    # --- calculate control here --- #
    error = calculate_postion(line)
    delta_u = pid_control(error)
    v1 = 60 - delta_u
    v2 = 60 + delta_u
