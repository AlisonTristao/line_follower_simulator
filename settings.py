import random
from simulator import GameSimulation, SimulationConfig, MEDIUM, LEMNISCATE


def settings():

    # fix the seed for reproducibility
    seed = 42 # None
    random.seed(seed)

    print("press esc to quit")
    print("seed =", seed)

    sim_config = SimulationConfig(
        screen_size=MEDIUM,
        fps=80,
        length=100,
        width=100,
        scale=250,
        render=3,
        track_type=LEMNISCATE,
        track_length=0.02,
        sensor_spacing=0.008,
    )
    sim = GameSimulation(sim_config)

    # Initialize future points for visualization
    sim.set_future_points(count=45, space=3)

    return sim