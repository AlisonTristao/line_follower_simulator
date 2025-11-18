from dataclasses import dataclass
import numpy as np
import random
from simulator import GameSimulation, SimulationConfig, MEDIUM, LEMNISCATE

# fix the seed for reproducibility
seed = 42 # None
random.seed(seed)

print("press esc to quit")
print("press p to pause/unpause the simulation and aplly perturbations")
print("seed =", seed)

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
    sim.set_encoders_count(car_cfg.encoder_precision)
    sim.set_optical_flow_distance(car_cfg.optical_flow_distance)

    sim.set_future_points(count=45, space=3)

    # ------------------------------------------------------------------
    # Main control loop
    # ------------------------------------------------------------------

    # H1 
    H1 = np.zeros((2,2))
    H1[0,0] = car_cfg.wheels_radius/2
    H1[0,1] = car_cfg.wheels_radius/2
    H1[1,0] = car_cfg.wheels_radius/car_cfg.wheels_distance
    H1[1,1] = -car_cfg.wheels_radius/car_cfg.wheels_distance

    H2 = np.zeros((2,2))
    H2[0,0] = 0
    H2[0,1] = 1
    H2[1,0] = 1/car_cfg.optical_flow_distance
    H2[1,1] = 0

    enc_left, enc_right = 0, 0
    dx, dy = 0, 0

    v1 = v2 = 0.0
    while True:
        data = sim.step(v1, v2)
        if data is None:
            break

        line, future_pts, car = data
        print("----- New Step -----")
        print(car.get_data())
        enc = car.get_encoders()
        enc_left += enc[0]
        enc_right += enc[1]
        opt = car.get_optical_flow()
        dx += opt[0]
        dy += opt[1]
        print(H1 @ [enc_left, enc_right])
        print(H2 @ [dx, dy]/sim.FPS)

        # TODO: Implement control algorithm to update v1 and v2
        # currently the car will remain stationary

        v1 = 15
        v2 = 10
        
if __name__ == "__main__":
    main()
