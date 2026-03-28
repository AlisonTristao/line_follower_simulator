import numpy as np
from settings import *

def main(sim) -> None:
    # ------------------------------------------------------------------
    # Main control loop - receives data from real robot via serial
    # ------------------------------------------------------------------

    while True:
        # TODO: Receive delta_x, delta_y from real robot via serial
        delta_x = 0.0
        delta_y = 0.0

        data = sim.step(delta_x, delta_y)
        if data is None:
            break

        # ---------------------------------------------------------------
        # Receive visualization data from simulator
        # ---------------------------------------------------------------

        line, future_pts = data
        
if __name__ == "__main__":
    sim = settings()
    main(sim)
