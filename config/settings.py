import random

from .simulator import FULL, GameSimulation, SimulationConfig

METER_PER_SCALE = 3.0


def settings():
    # Fix the seed for reproducibility.
    seed = 42
    random.seed(seed)

    print("press esc to quit")
    print("seed =", seed)

    sim_config = SimulationConfig(
        screen_size=FULL,
        fps=300,
        length=12,
        width=6,
        scale=500,
        render=2,
        tail_time=0.01,
        # Robot dimensions in meters.
        car_size=0.10,
        front_sensor_distance=0.12,
        front_sensor_size=0.10,
        side_sensor_distance_x=0.05,
        side_sensor_distance_y=0.05,
        side_sensor_size=0.01,
        track_file_path="tracks/track_teste.tfg",
    )
    sim = GameSimulation(sim_config)

    return sim
