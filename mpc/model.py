import math
import numpy as np

def sinc(theta):
    # unnormalised sinc: sin(theta)/theta
    return np.sinc(np.asarray(theta) / np.pi)

def dsinc(theta):
    # derivative of the unnormalised sinc
    theta = np.asarray(theta, dtype=float)
    small = np.abs(theta) < 1e-4
    t = np.where(small, 1.0, theta)
    return np.where(small, -theta / 3, (t * np.cos(t) - np.sin(t)) / t ** 2)

class LineFollowerQLPV:
    """
    exact qLPV embedding of the differential drive car, written in the car frame of the instant k.

    states:     x = [w_l, w_r, theta, X, Y]  (wheels speed [rad/s], heading [rad], lateral and forward position [m])
    inputs:     u = [u_l, u_r]               (% of PWM)

        w(k+1)     = a w(k) + b (u(k) + d)
        theta(k+1) = theta(k) + Ts r/L (w_l - w_r)(k+1)
        X(k+1)     = X(k) + v(k+1) Ts sin(theta(k))        v = r/2 (w_l + w_r)
        Y(k+1)     = Y(k) + v(k+1) Ts cos(theta(k))

        x(k+1) = A(rho(k)) x(k) + B(rho(k)) (u(k) + d),   A(rho) = A0 + sum_i rho_i A_i (the same for B)

    the bilinear term v sin(theta) has two exact factorizations (embedding):
        "sin_cos": rho = [sin(theta), cos(theta)]
                   X(k+1) = X(k) + rho_1 Ts v(k+1)          -> lateral position linear in the speed
        "sinc":    rho = [cos(theta), v(k+1) sinc(theta)]
                   X(k+1) = X(k) + rho_2 Ts theta(k)        -> lateral position linear in the heading

    the scheduling proxy is evaluated on z = [x(k), x(k+1)] (v(k+1) depends on u(k) in "sinc").
    d is an input disturbance (estimated online, gives offset-free tracking).
    theta positive turns right, X positive to the right and Y positive forward.
    """
    nx = 5
    nu = 2
    nrho = 2

    # outputs: theta, X, Y
    output_index = (2, 3, 4)

    def __init__(self, Ts, wheels_radius, wheels_distance, wheels_RPM, ke_l, ke_r, accommodation_time_l, accommodation_time_r,
                 embedding="sinc"):
        if embedding not in ("sin_cos", "sinc"):
            raise ValueError("embedding must be 'sin_cos' or 'sinc'")
        self.embedding = embedding
        self.Ts = Ts
        self.r = wheels_radius

        # rad/s for 1% of PWM
        Ke = 2 * math.pi * wheels_RPM / 6000
        self.Ke = Ke

        # motors (5 tau = accommodation time)
        a_l = math.exp(-5 * Ts / accommodation_time_l)
        a_r = math.exp(-5 * Ts / accommodation_time_r)
        b_l = Ke * ke_l * (1 - a_l)
        b_r = Ke * ke_r * (1 - a_r)
        self.alpha = np.array([a_l, a_r])
        self.beta = np.array([b_l, b_r])

        # kinematics
        c_t = Ts * wheels_radius / wheels_distance
        c_v = Ts * wheels_radius / 2
        self.c_theta = c_t
        self.c_v = c_v

        nx, nu = self.nx, self.nu
        A0 = np.eye(nx)
        A0[0, 0], A0[1, 1] = a_l, a_r
        A0[2, :2] = [c_t * a_l, -c_t * a_r]
        B0 = np.zeros((nx, nu))
        B0[0, 0], B0[1, 1] = b_l, b_r
        B0[2] = [c_t * b_l, -c_t * b_r]

        # rows multiplied by the speed v(k+1): c_v (a w + b u)
        def speed_row(row):
            A, B = np.zeros((nx, nx)), np.zeros((nx, nu))
            A[row, :2] = [c_v * a_l, c_v * a_r]
            B[row] = [c_v * b_l, c_v * b_r]
            return A, B

        if embedding == "sin_cos":
            A1, B1 = speed_row(3)           # X: sin(theta) v(k+1)
            A2, B2 = speed_row(4)           # Y: cos(theta) v(k+1)
            self.rho_min = np.array([-1.0, -1.0])
            self.rho_max = np.array([1.0, 1.0])
        else:
            A1, B1 = speed_row(4)           # Y: cos(theta) v(k+1)
            A2, B2 = np.zeros((nx, nx)), np.zeros((nx, nu))
            A2[3, 2] = Ts                   # X: v(k+1) sinc(theta) theta
            # max speed with 20% of margin for disturbances
            v_max = 1.2 * 100 * Ke * wheels_radius
            self.rho_min = np.array([-1.0, -v_max])
            self.rho_max = np.array([1.0, v_max])

        # (1 + nrho, ...) affine decomposition
        self.A_aff = np.stack((A0, A1, A2))
        self.B_aff = np.stack((B0, B1, B2))

    # --- qLPV model --- #

    def matrices(self, P):
        """
        P: (N, nrho) scheduling trajectory -> A (N, nx, nx), B (N, nx, nu)
        """
        P = np.atleast_2d(P)
        w = np.column_stack((np.ones(len(P)), P))
        return np.einsum("ni,ijk->njk", w, self.A_aff), np.einsum("ni,ijk->njk", w, self.B_aff)

    def pairs(self, S):
        # state sequence (M+1, nx) -> scheduling arguments z = [x(j), x(j+1)], (M, 2 nx)
        S = np.asarray(S)
        return np.hstack((S[:-1], S[1:]))

    def f_rho(self, z):
        # scheduling proxy, z: (..., 2 nx) -> (..., nrho)
        z = np.asarray(z)
        theta = z[..., 2]
        if self.embedding == "sin_cos":
            return np.stack((np.sin(theta), np.cos(theta)), axis=-1)
        v_next = self.r / 2 * (z[..., self.nx] + z[..., self.nx + 1])
        return np.stack((np.cos(theta), v_next * sinc(theta)), axis=-1)

    def jacobian_rho(self, z):
        # d f_rho / dz evaluated at z: (nrho, 2 nx)
        theta = z[2]
        J = np.zeros((self.nrho, 2 * self.nx))
        if self.embedding == "sin_cos":
            J[:, 2] = [math.cos(theta), -math.sin(theta)]
        else:
            v_next = self.r / 2 * (z[self.nx] + z[self.nx + 1])
            J[0, 2] = -math.sin(theta)
            J[1, 2] = v_next * dsinc(theta)
            J[1, self.nx:self.nx + 2] = self.r / 2 * sinc(theta)
        return J

    def saturate_rho(self, P):
        return np.clip(P, self.rho_min, self.rho_max)

    def step(self, x, u, d=0.0):
        # exact nonlinear model (for validation): the wheels do not depend on rho
        x = np.asarray(x, dtype=float)
        x_next = x.copy()
        x_next[:2] = self.alpha * x[:2] + self.beta * (np.asarray(u) + d)
        A, B = self.matrices(self.f_rho(np.concatenate((x, x_next)))[None])
        return A[0] @ x + B[0] @ (np.asarray(u) + d)

    # --- measurements and car frame --- #

    def state(self, wheels_speed):
        # x(k) in the car frame of the instant k
        return np.array([wheels_speed[0], wheels_speed[1], 0.0, 0.0, 0.0])

    def frame_shift(self, wheels_speed):
        """
        pose (theta, X, Y) of the car at k written in the car frame of k-1 (odometry, exact for this model)
        """
        w_l, w_r = wheels_speed
        return np.array([self.c_theta * (w_l - w_r), 0.0, self.c_v * (w_l + w_r)])

    def realign_states(self, S, pose):
        # writes a state trajectory (M, nx) given in the frame of k-1 in the frame of k
        S = np.array(S, dtype=float)
        theta0, X0, Y0 = pose
        c, s = math.cos(theta0), math.sin(theta0)
        dX, dY = S[:, 3] - X0, S[:, 4] - Y0
        S[:, 2] -= theta0
        S[:, 3] = c * dX - s * dY
        S[:, 4] = s * dX + c * dY
        return S

    def input_disturbance(self, w_prev, w_now, u_prev):
        # input disturbance that explains the last wheels step: w(k) = a w(k-1) + b (u(k-1) + d)
        return (np.asarray(w_now) - self.alpha * np.asarray(w_prev)) / self.beta - np.asarray(u_prev)
