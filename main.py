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
sensor_spacing      = 0.008 # meters

# motor constants
ke                  = 1.0 # static gain of V1 => (y = ke * v)
accommodation_time  = 1.0 # seconds

# track caracteristics
track_type          = CIRCLE
track_length        = 0.015 # meters

# future points
future_points       = 6    # number of future points
future_spacing      = 40    # resolutuin of the track

# setup the simulation
start_simulation(screen_size, screen_fps, seed=track_seed, track_type=track_type, track_length=track_length, sensor_spacing=sensor_spacing)

# setup the car dynamics
set_car_dynamics(wheels_radius, wheels_distance, wheels_RPM, ke, accommodation_time, sensor_distance, sensor_count)

# setup the future points
set_future_points(future_points, future_spacing)

# --- put your code here --- #

v1 = 0
v2 = 0

while True:
    # --- step the simulaine, future_points, speed, omega tion here --- #
    data = step_simulation(v1, v2)
    if data is None: 
        break
    else:
        line, future_points, speed, omega = data