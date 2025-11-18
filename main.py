import numpy as np
from settings import *

def main(sim, car_cfg) -> None:
    # ------------------------------------------------------------------
    # Main control loop
    # ------------------------------------------------------------------

    v1 = v2 = 0.0
    last_erro = 0.0
    while True:
        data = sim.step(v1, v2)
        if data is None:
            break

        # ---------------------------------------------------------------
        # your code here
        # --------------------------------------------------------------

        line, future_pts, car = data
        
if __name__ == "__main__":
    sim, car_cfg = settings()
    main(sim, car_cfg)
