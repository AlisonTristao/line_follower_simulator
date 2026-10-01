import numpy as np

from .model import LineFollowerQLPV
from .qlpv_mpc import QLPVMPC

def track_reference(points):
    """
    future track points in the car frame (N, 2) [x lateral, y forward] -> reference (N, 3) [theta, X, Y]
    theta is the heading of the track tangent at each point
    """
    points = np.asarray(points, dtype=float)
    x, y = points[:, 0], points[:, 1]
    theta = np.arctan2(np.gradient(x), np.gradient(y))
    return np.column_stack((theta, x, y))

def contouring_weights(ref, Q, Q_N):
    """
    stage weights (N, 3, 3) with the position error written along the track:
        e_lat = (p - r) . n,  e_lon = (p - r) . t,  t = (sin theta_r, cos theta_r), n = (cos theta_r, -sin theta_r)
    Q, Q_N = [q_theta, q_lateral, q_longitudinal]
    """
    N = len(ref)
    q = np.tile(np.asarray(Q, dtype=float), (N, 1))
    q[-1] = Q_N
    s, c = np.sin(ref[:, 0]), np.cos(ref[:, 0])
    n = np.column_stack((c, -s))
    t = np.column_stack((s, c))
    W = np.zeros((N, 3, 3))
    W[:, 0, 0] = q[:, 0]
    W[:, 1:, 1:] = q[:, 1, None, None] * n[:, :, None] * n[:, None, :] + q[:, 2, None, None] * t[:, :, None] * t[:, None, :]
    return W

class LineFollowerController:
    """
    qLPV MPC for the line follower: builds the reference from the future points of the track,
    estimates the input disturbance (offset-free) and keeps the car frame of the previous solution.

    contouring = True:  Q = [theta, lateral, longitudinal] (errors along the track)
    contouring = False: Q = [theta, X, Y] (errors in the car frame)
    """
    def __init__(self, model: LineFollowerQLPV, horizon, Q, R, Rd, Q_N=None, u_min=-100, u_max=100,
                 scheduling="taylor", disturbance_filter=0.2, contouring=True, **scheduling_kwargs):
        self.model = model
        self.mpc = QLPVMPC(model, horizon, Q, R, Rd, Q_N, u_min, u_max, scheduling, **scheduling_kwargs)
        self.Q = np.asarray(Q, dtype=float)
        self.Q_N = self.Q if Q_N is None else np.asarray(Q_N, dtype=float)
        self.contouring = contouring
        self.disturbance_filter = disturbance_filter
        self.reset()

    def reset(self):
        self.mpc.reset()
        self.u = np.zeros(self.model.nu)
        self.w_prev = np.zeros(self.model.nu)
        self.d = np.zeros(self.model.nu)
        self.ref = None

    def step(self, wheels_speed, future_points):
        w = np.asarray(wheels_speed, dtype=float)

        # input disturbance from the last wheels step
        d_now = self.model.input_disturbance(self.w_prev, w, self.u)
        self.d += self.disturbance_filter * (d_now - self.d)
        self.w_prev = w

        self.ref = track_reference(future_points)
        W = contouring_weights(self.ref, self.Q, self.Q_N) if self.contouring else None
        self.u = self.mpc.step(self.model.state(w), self.ref, self.d, frame=self.model.frame_shift(w), W=W)
        return self.u

    @property
    def name(self):
        return f"qLPV MPC ({self.model.embedding}, {self.mpc.scheduling})"

    @property
    def stats(self):
        return self.mpc.stats

    def prediction(self):
        # (N, 3) predicted [theta, X, Y]
        return self.mpc.predicted_outputs()

    def scheduling_trajectory(self):
        return self.mpc.P
