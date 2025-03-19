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

while True:
    line = step_simulation(v1, v2)
    if line is None:
        break
    
    # loop until the car reaches the end of the track
    # v1 = 20
    # v2 = 20
