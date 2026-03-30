import random
import numpy as np
from simulator import GameSimulation, SimulationConfig, FULL, CSV_TRACK

METER_PER_SCALE = 3.0

def settings():

    # fix the seed for reproducibility
    seed = 42 # None
    random.seed(seed)

    print("press esc to quit")
    print("seed =", seed)

    sim_config = SimulationConfig(
        screen_size=FULL,
        fps=300,
        length=7,                      # track length in meters
        width=7,                        # track width in meters
        scale=500, # pixels per unity
        meter_per_scale = METER_PER_SCALE,
        render=2,                        # number of chuncks render
        tail_time=0.01,
        # Robot dimensions in METERS
        car_size=0.10,                   # Car width in meters
        front_sensor_distance=0.12,      # Distance from car center to front sensor in meters
        front_sensor_size=0.10,          # Front sensor length in meters
        side_sensor_distance_x=0.10,     # Horizontal distance from car center to side sensors in meters (left/right)
        side_sensor_distance_y=0.10,     # Vertical distance from car center to side sensors in meters (forward/backward)
        side_sensor_size=0.03,           # Side sensor diameter in meters
        # track generation configuration
        track_type=CSV_TRACK,          # type of format
        track_path="pista.csv"
        #track_noise=0.225,              # noise level as a percentage of track radius
        #track_radius=3                 # track radius in meters (for circular tracks) or size of the figure (for lemniscate)

    )
    sim = GameSimulation(sim_config)

    return sim