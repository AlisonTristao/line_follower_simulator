import os

# the problems are small: multithreaded BLAS only adds overhead (100x slower solves with 12 threads)
for _var in ("OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "OMP_NUM_THREADS"):
    os.environ.setdefault(_var, "1")
try:
    from threadpoolctl import threadpool_limits
    threadpool_limits(1)
except ImportError:
    pass

from .model import LineFollowerQLPV
from .qlpv_mpc import QLPVMPC, solve_box_qp
from .scheduling import Scheduling, Frozen, WarmStart, Taylor, Iterative, make_scheduling, STRATEGIES
from .line_follower import LineFollowerController, track_reference
from .gpc import LineFollowerGPC
