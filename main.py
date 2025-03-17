from simulator import *

last_mediam = 0
def calculate_postion(line):
    global last_mediam
    sum = 0
    pesos = 0
    for i in range(len(line)):
        sum += line[i] * (i+1)
        pesos += line[i]

    if pesos == 0:
        mediam = last_mediam
    else:
        mediam = sum/pesos
        last_mediam = mediam

    return mediam - len(line)/2

u = 0
kp = 0.15
kd = 0.02
last_error = 0
running = True
while running:
    line = abs(1 - step_simulation(80 +u, 80 -u)/255)

    # --- calculate control here --- #
    point = calculate_postion(line)
    error = 0 - point

    u = kp * error + kd * (error - last_error)

    last_error = point
    if line is False:
        running = False

