from dataclasses import dataclass
import random
import numpy as np
from simulator import GameSimulation, SimulationConfig, MEDIUM, LEMNISCATE

# fix the seed for reproducibility
seed = 42 # None
random.seed(seed)

print("press esc to quit")
print("press p to pause/unpause the simulation and aplly perturbations")
print("seed =", seed)

last = 0.0
def calculate_point(line):
    # index s index n index s index n 
    arr = np.array(line)
    mediam = np.median(np.where(arr != 0)[0]) + 1
    if mediam != None:
        last = (mediam - len(arr)/2)/len(arr)
    return last

@dataclass
class CarConfig:
    """Parameters defining the vehicle model."""

    wheels_radius: float = 0.04
    wheels_distance: float = 0.15
    wheels_RPM: int = 1000
    ke_l: float = 1.0
    ke_r: float = 1.0
    accommodation_time_l: float = 0.62
    accommodation_time_r: float = 0.58
    sensor_distance: float = 0.15
    sensor_count: int = 15

def main() -> None:

    sim_config = SimulationConfig(
        screen_size=MEDIUM,
        fps=80,
        length=100,
        width=100,
        scale=300,
        render=4,
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

    sim.set_future_points(count=45, space=3)

    # ------------------------------------------------------------------
    # Main control loop
    # ------------------------------------------------------------------

    v1 = v2 = 0.0
    last_erro = 0.0
    while True:
        data = sim.step(v1, v2)
        if data is None:
            break

        line, future_pts, speed, omega, wheel_omega = data

        tensao_media = 80

        erro = calculate_point(line)
        derivada_erro = (erro - last_erro)/0.0125
        last_erro = erro

        Kp = 100
        Kd = 4

        v1 = tensao_media + (Kp * erro + Kd * derivada_erro)
        v2 = tensao_media - (Kp * erro + Kd * derivada_erro)

if __name__ == "__main__":
    main()
