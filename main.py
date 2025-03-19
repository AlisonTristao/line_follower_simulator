from simulator import *

# car constants
wheels_radius       = 0.04 # meters
wheels_distance     = 0.10 # meters
wheels_RPM          = 3000 # RPM

# motor constants
ke                  = 1.0 # static gain of V1 => (y = ke * v) * RPM/60 => Hz
accommodation_time  = 1.0 # seconds

# setup the simulation
start_simulation(fps=80)

# setup the car dynamics
set_car_dynamics(wheels_radius, wheels_distance, wheels_RPM, ke, accommodation_time)

# --- insert your code here --- #
v1 = 10
v2 = 10

# example for calculating the position of the line
last_mediam = 0
def calculate_postion(line):
    global last_mediam
    line = abs(1 - line/255)
    sum = 0
    pesos = 0
    for i in range(len(line)):
        sum += line[i] * (i+1)
        pesos += line[i]

    if pesos < 8:
        mediam = last_mediam
    else:
        mediam = sum/pesos
        last_mediam = mediam

    return mediam - len(line)/2

sample_time = 1/120
u = 0
kp = 0.3
ki = 0.4
kd = 0.05
last_error = 0
integral = 0

# example for calculating the control
def pid_control(error):
    global last_error, integral, kp, ki, kd, sample_time
    error = calculate_postion(line)
    integral += error * sample_time

    delta_u = kp * error + kd * (error - last_error)/sample_time + ki * integral 
    last_error = error
    return delta_u

while True:
    # --- step the simulation here --- #
    line = step_simulation(v1, v2)
    if line is None:
        break

    # --- calculate control here --- #
    error = calculate_postion(line)
    delta_u = pid_control(error)
    v1 = 90 - delta_u
    v2 = 90 + delta_u
