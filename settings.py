import random
import numpy as np
from simulator import GameSimulation, SimulationConfig, MEDIUM, LEMNISCATE, FULL

# Pre-calculated sine wave cache to avoid allocating 16KB per frame
# This is used in simulate_robot_data() and saves ~1MB/minute of garbage collection
SINE_WAVE_CACHE = 50 * np.sin(2 * np.pi * np.linspace(0, 10, 1000))


def settings():

    # fix the seed for reproducibility
    seed = 42 # None
    random.seed(seed)

    print("press esc to quit")
    print("seed =", seed)

    sim_config = SimulationConfig(
        screen_size=FULL,
        fps=80,
        length=100,
        width=50,
        scale=250,
        render=3,
        track_type=LEMNISCATE,
        track_length=0.02,
        sensor_spacing=0.008,
        # Robot dimensions in METERS
        car_size=0.10,                   # Car width in meters
        front_sensor_distance=0.12,      # Distance from car center to front sensor in meters
        front_sensor_size=0.10,          # Front sensor length in meters
        side_sensor_distance_x=0.10,     # Horizontal distance from car center to side sensors in meters (left/right)
        side_sensor_distance_y=0.10,     # Vertical distance from car center to side sensors in meters (forward/backward)
        side_sensor_size=0.03,           # Side sensor diameter in meters
    )
    sim = GameSimulation(sim_config)

    # Initialize future points for visualization
    sim.set_future_points(count=45, space=3)

    return sim