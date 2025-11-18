from dataclasses import dataclass
import numpy as np
import random
from simulator import GameSimulation, SimulationConfig, MEDIUM, LEMNISCATE

@dataclass
class CarConfig:
    """Parameters defining the vehicle model."""
    wheels_radius: float = 0.04
    wheels_distance: float = 0.15
    wheels_RPM: int = 1000
    ke_l: float = 1.0
    ke_r: float = 1.0
    accommodation_time_l: float = 0.6
    accommodation_time_r: float = 0.6
    sensor_distance: float = 0.15
    sensor_count: int = 15
    encoder_precision: int = 70
    optical_flow_distance: float = -0.1

def settings():

    # fix the seed for reproducibility
    seed = 42 # None
    random.seed(seed)

    print("press esc to quit")
    print("press p to pause/unpause the simulation and aplly perturbations")
    print("seed =", seed)

    sim_config = SimulationConfig(
        screen_size=MEDIUM,
        fps=80,
        length=100,
        width=100,
        scale=200,
        render=2,
        track_type=LEMNISCATE,
        track_length=0.02,
        sensor_spacing=0.008,
    )
    sim = GameSimulation(sim_config)

    car_cfg = CarConfig()
    sim.setup_car_dynamics(
        wheels_radius=car_cfg.wheels_radius,
        wheels_distance=car_cfg.wheels_distance,
        wheels_RPM=car_cfg.wheels_RPM,
        ke_l=car_cfg.ke_l,
        ke_r=car_cfg.ke_r,
        kq=1,
        accommodation_time_l=car_cfg.accommodation_time_l,
        accommodation_time_r=car_cfg.accommodation_time_r,
        sensor_distance=car_cfg.sensor_distance,
        sensor_count=car_cfg.sensor_count,
    )
    sim.set_encoders_count(car_cfg.encoder_precision)
    sim.set_optical_flow_distance(car_cfg.optical_flow_distance)

    sim.set_future_points(count=45, space=3)

    return sim