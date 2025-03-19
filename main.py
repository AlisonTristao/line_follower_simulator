from simulator import *

last_mediam = 0
def calculate_postion(line):
    global last_mediam
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
running = True
while running:
    line = abs(1 - step_simulation(90 +u, 90 -u)/255)

    # --- calculate control here --- #
    point = calculate_postion(line)
    error = 0 - point
    integral += error * sample_time

    u = kp * error + kd * (error - last_error)/sample_time + ki * integral 

    last_error = error
    if line is False:
        running = False

