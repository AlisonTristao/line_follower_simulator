from simulator import *

# screen settings => sizes FULL, MEDIUM, SMALL
screen_size = MEDIUM
screen_fps = 80
track_seed = 1111

# car constants
wheels_radius       = 0.04  # meters
wheels_distance     = 0.10  # meters
wheels_RPM          = 1000  # RPM
sensor_distance     = 0.10  # meters
sensor_count        = 15    

# motor constants
ke                  = 1.0 # static gain of V1 => (y = ke * v)
accommodation_time  = 1.0 # seconds

# track caracteristics
track_type          = CIRCLE
track_length        = 0.015 # meters
sensor_spacing      = 0.008 # meters

# future points
future_points       = 5     # number of future points
future_spacing      = 30    # resolutuin of the track

# setup the simulation
start_simulation(screen_size, screen_fps, seed=track_seed, track_type=track_type, track_length=track_length, sensor_spacing=sensor_spacing)

# setup the car dynamics
set_car_dynamics(wheels_radius, wheels_distance, wheels_RPM, ke, accommodation_time, sensor_distance, sensor_count)

# setup the future points
set_future_points(future_points, future_spacing)

# --- insert your code here --- #
v1 = 0
v2 = 0

while True:
    # --- step the simulation here --- #
    line, future_points = step_simulation(v1, v2)
    if line is None or future_points is None:
        break

    # --- insert your code here --- #