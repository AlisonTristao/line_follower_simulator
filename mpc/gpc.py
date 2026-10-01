import math
import time
import numpy as np

class LineFollowerGPC:
    """
    GPC linearized at theta = 0 (the previous controller of the project), computed from the motor
    parameters (no csv / octave files).

    each wheel angle phi follows the CARIMA model (Delta u as input):
        (1 - a z^-1)(1 - z^-1)^2 phi(k) = Ts b z^-1 Delta u(k)

    outputs (car frame of the instant k, linear in the wheels angle):
        theta = r/L (phi_l - phi_r)     heading
        d     = r/2 (phi_l + phi_r)     travelled distance

    free response: homogeneous recursion from the last 3 measured wheel angles (future Delta u = 0)
    forced response: step response g of each wheel (Toeplitz matrix with N_u columns)

    reference (linearized, theta = 0):
        "lookahead": theta_r(j) = x_j / d0    (lateral offset of the future point over a look-ahead distance)
        "tangent":   theta_r(j) = heading of the track tangent
        d_r(j) = y_j

    the control law is the unconstrained GPC: Delta U = K (r - f), the input is saturated afterwards.
    """
    def __init__(self, Ts, wheels_radius, wheels_distance, wheels_RPM, ke_l, ke_r, accommodation_time_l, accommodation_time_r,
                 horizon=45, control_horizon=5, q_theta=0.5, q_distance=1.0, lamb=1e-3, d0=0.3,
                 theta_reference="lookahead", u_min=-100, u_max=100):
        self.Ts = Ts
        self.N = horizon
        self.Nu = control_horizon
        self.d0 = d0
        self.theta_reference = theta_reference
        self.u_min, self.u_max = u_min, u_max
        self.name = f"GPC (N={horizon}, Nu={control_horizon}, {theta_reference})"

        Ke = 2 * math.pi * wheels_RPM / 6000
        alpha = np.array([math.exp(-5 * Ts / accommodation_time_l), math.exp(-5 * Ts / accommodation_time_r)])
        beta = Ke * np.array([ke_l, ke_r]) * (1 - alpha)
        self.c_theta = wheels_radius / wheels_distance
        self.c_d = wheels_radius / 2

        # A~(z^-1) = (1 - a z^-1)(1 - z^-1)^2 = 1 + a1 z^-1 + a2 z^-2 + a3 z^-3, for each wheel (2, 3)
        self.a = np.array([np.polymul([1, -a], [1, -2, 1])[1:] for a in alpha])

        # free response matrix: phi_f(k+j) = F[j] @ [phi(k), phi(k-1), phi(k-2)]  (N, 3) for each wheel
        self.F = np.stack([self._free_matrix(a) for a in self.a])

        # step response of Delta u -> phi and the dynamic matrix (N, Nu) for each wheel
        g = np.stack([self._step_response(a, Ts * b) for a, b in zip(self.a, beta)])
        self.g = g
        G = np.stack([self._toeplitz(gw) for gw in g])

        # outputs [theta (N); d (N)], decision [Delta u_l (Nu); Delta u_r (Nu)]
        self.G = np.block([
            [self.c_theta * G[0], -self.c_theta * G[1]],
            [self.c_d * G[0], self.c_d * G[1]],
        ])
        Q = np.diag(np.concatenate((np.full(horizon, q_theta / horizon), np.full(horizon, q_distance / horizon))))
        R = np.eye(2 * control_horizon) * lamb / control_horizon
        K = np.linalg.solve(self.G.T @ Q @ self.G + R, self.G.T @ Q)
        self.K = K
        # only the first move of each wheel is applied
        self.K1 = K[[0, control_horizon]]
        self.reset()

    def _free_matrix(self, a):
        N = self.N
        F = np.zeros((N, 3))
        # history rows: phi(k), phi(k-1), phi(k-2) as unit vectors
        hist = [np.eye(3)[0], np.eye(3)[1], np.eye(3)[2]]
        for j in range(N):
            nxt = -(a[0] * hist[0] + a[1] * hist[1] + a[2] * hist[2])
            F[j] = nxt
            hist = [nxt, hist[0], hist[1]]
        return F

    def _step_response(self, a, b):
        # phi(k) for Delta u = 1 at k = 0: phi(k+1) = -a1 phi(k) - a2 phi(k-1) - a3 phi(k-2) + b Delta u(k)
        phi = [0.0, 0.0, 0.0]
        g = []
        for j in range(self.N):
            nxt = -(a[0] * phi[0] + a[1] * phi[1] + a[2] * phi[2]) + (b if j == 0 else 0.0)
            g.append(nxt)
            phi = [nxt, phi[0], phi[1]]
        return np.array(g)

    def _toeplitz(self, g):
        G = np.zeros((self.N, self.Nu))
        for i in range(self.Nu):
            G[i:, i] = g[:self.N - i]
        return G

    def reset(self):
        self.u = np.zeros(2)
        # last 3 wheel angles (phi(k), phi(k-1), phi(k-2)) for each wheel, relative to phi(k)
        self.phi = np.zeros((2, 3))
        self.ref = None
        self.free = None
        self.dU = None
        self.stats = {}

    def reference(self, future_points):
        points = np.asarray(future_points, dtype=float)
        x, y = points[:, 0], points[:, 1]
        if self.theta_reference == "lookahead":
            theta = x / self.d0
        else:
            theta = np.arctan2(np.gradient(x), np.gradient(y))
        return np.column_stack((theta, x, y))

    def step(self, wheels_speed, future_points):
        t0 = time.perf_counter()
        w = np.asarray(wheels_speed, dtype=float)

        # integrate the wheel angles and write them relative to phi(k) (the outputs are reset at each instant)
        phi_k = self.phi[:, 0] + w * self.Ts
        self.phi = np.column_stack((phi_k, self.phi[:, :2])) - phi_k[:, None]

        # free response of each wheel (N,)
        f_l, f_r = self.F[0] @ self.phi[0], self.F[1] @ self.phi[1]
        self.free = np.concatenate((self.c_theta * (f_l - f_r), self.c_d * (f_l + f_r)))

        self.ref = self.reference(future_points)
        r = np.concatenate((self.ref[:, 0], self.ref[:, 2]))

        self.dU = self.K @ (r - self.free)
        self.u = np.clip(self.u + self.dU[[0, self.Nu]], self.u_min, self.u_max)
        self.stats = {"time": time.perf_counter() - t0, "qp": 0, "qp_iters": 0, "rho_error": 0.0}
        return self.u.copy()

    def prediction(self):
        """
        (N, 3) predicted [theta, X, Y]: theta and d from the GPC prediction (free + forced),
        X and Y integrated from them only for visualization
        """
        if self.free is None:
            return None
        y = self.free + self.G @ self.dU
        theta, d = y[:self.N], y[self.N:]
        ds = np.diff(np.concatenate(([0.0], d)))
        heading = np.concatenate(([0.0], theta[:-1]))
        return np.column_stack((theta, np.cumsum(ds * np.sin(heading)), np.cumsum(ds * np.cos(heading))))

    def scheduling_trajectory(self):
        return None
