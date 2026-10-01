import time
import numpy as np
from scipy.optimize import minimize

from .scheduling import make_scheduling

def solve_box_qp(H, g, lb, ub, x0=None, max_iter=50):
    """
    min 1/2 x'Hx + g'x  s.t.  lb <= x <= ub   (H positive definite)

    primal-dual active set (semismooth Newton on x = clip(x - D^-1 (Hx + g))), warm started by x0.
    returns (x, iterations); falls back to L-BFGS-B if the active set does not settle.
    """
    d = np.diag(H)
    x = np.clip(-g / d if x0 is None else x0, lb, ub)
    lower = upper = None
    for it in range(1, max_iter + 1):
        t = x - (H @ x + g) / d
        new_lower, new_upper = t <= lb, t >= ub
        if lower is not None and np.array_equal(new_lower, lower) and np.array_equal(new_upper, upper):
            return x, it - 1
        lower, upper = new_lower, new_upper
        free = ~(lower | upper)

        x = np.where(lower, lb, np.where(upper, ub, 0.0))
        if free.any():
            bound = ~free
            rhs = -g[free]
            if bound.any():
                rhs -= H[np.ix_(free, bound)] @ x[bound]
            x[free] = np.linalg.solve(H[np.ix_(free, free)], rhs)

    res = minimize(lambda z: (0.5 * z @ H @ z + g @ z, H @ z + g), np.clip(x, lb, ub),
                   jac=True, method="L-BFGS-B", bounds=list(zip(lb, ub)))
    return res.x, max_iter

class QLPVMPC:
    """
    qLPV MPC: for a given scheduling trajectory P_k the prediction is linear in U_k and the problem is a QP

        min  sum_{j=1}^{N} |y(k+j|k) - r(k+j)|^2_Q  (Q_N at j = N)
           + sum_{j=0}^{N-1} |u(k+j|k)|^2_R + |du(k+j|k)|^2_Rd
        s.t. x(k+j+1|k) = A(rho(k+j|k)) x(k+j|k) + B(rho(k+j|k)) (u(k+j|k) + d)
             u_min <= u(k+j|k) <= u_max

    model:      qLPV model (see mpc.model.LineFollowerQLPV)
    horizon:    N
    Q, Q_N:     output weights (diagonal, length ny); step() also accepts full stage weights W (N, ny, ny)
    R, Rd:      input and input variation weights (diagonal, length nu)
    scheduling: strategy name or object (see mpc.scheduling)
    """
    def __init__(self, model, horizon, Q, R, Rd, Q_N=None, u_min=-100, u_max=100, scheduling="taylor", **scheduling_kwargs):
        self.model = model
        self.N = horizon
        self.scheduling = make_scheduling(scheduling, **scheduling_kwargs)

        nu, N = model.nu, horizon
        self.out = list(model.output_index)
        ny = len(self.out)
        self.ny = ny

        Q = np.diag(np.broadcast_to(np.asarray(Q, dtype=float), (ny,)))
        Q_N = Q if Q_N is None else np.diag(np.broadcast_to(np.asarray(Q_N, dtype=float), (ny,)))
        self.W = np.concatenate((np.tile(Q, (N - 1, 1, 1)), Q_N[None]))
        self.r = np.tile(np.broadcast_to(np.asarray(R, dtype=float), (nu,)), N)
        rd = np.tile(np.broadcast_to(np.asarray(Rd, dtype=float), (nu,)), N)
        self.rd = rd

        # du = D U - e0,  e0 = [u(k-1), 0, ..., 0]
        D = np.eye(N * nu) - np.eye(N * nu, k=-nu)
        self.H_u = np.diag(self.r) + D.T @ (rd[:, None] * D)
        self.Dt_rd = D.T * rd

        self.lb = np.tile(np.broadcast_to(np.asarray(u_min, dtype=float), (nu,)), N)
        self.ub = np.tile(np.broadcast_to(np.asarray(u_max, dtype=float), (nu,)), N)

        self.reset()

    def reset(self):
        self.u_prev = np.zeros(self.model.nu)
        self.S = None       # predicted states (N+1, nx)
        self.P = None       # scheduling estimate (N, nrho)
        self.U = None       # optimal inputs (N, nu)
        self.stats = {}

    def predict(self, P, x0, d):
        """
        lifted prediction X = free + Gamma U for the scheduling trajectory P
            free  (N, nx)          states for U = 0
            Gamma (N, nx, N*nu)
        """
        model, N = self.model, self.N
        nx, nu = model.nx, model.nu
        A, B = model.matrices(P)
        Bd = B @ d

        free = np.empty((N, nx))
        Gamma = np.zeros((N, nx, N * nu))
        x = x0
        G = np.zeros((nx, N * nu))
        for j in range(N):
            x = A[j] @ x + Bd[j]
            cols = j * nu
            if cols:
                G[:, :cols] = A[j] @ G[:, :cols]
            G[:, cols:cols + nu] = B[j]
            free[j] = x
            Gamma[j] = G
        return free, Gamma

    def solve_qp(self, P, x0, ref, d, U0=None, W=None):
        N, nu = self.N, self.model.nu
        W = self.W if W is None else W
        free, Gamma = self.predict(P, x0, d)

        Gy = Gamma[:, self.out, :]                                  # (N, ny, N*nu)
        err = free[:, self.out] - ref                               # (N, ny)
        WG = np.einsum("nab,nbk->nak", W, Gy)

        e0 = np.zeros(N * nu)
        e0[:nu] = self.u_prev
        H = Gy.reshape(N * self.ny, -1).T @ WG.reshape(N * self.ny, -1) + self.H_u
        g = np.einsum("nak,na->k", WG, err) - self.Dt_rd @ e0

        U, iters = solve_box_qp(H, g, self.lb, self.ub, U0)
        S = np.vstack((x0, free + Gamma @ U))
        return U.reshape(N, nu), S, iters

    def step(self, x0, ref, d=None, frame=None, W=None):
        """
        x0:    current state x(k) (in the current frame)
        ref:   (N, ny) reference for y(k+1), ..., y(k+N)
        d:     input disturbance (nu,)
        frame: pose of the current frame written in the previous one (moving frame models), or None
        W:     (N, ny, ny) stage weights for this sample (default: diag(Q) and diag(Q_N))
        returns u(k)
        """
        t0 = time.perf_counter()
        model, N = self.model, self.N
        d = np.zeros(model.nu) if d is None else np.asarray(d, dtype=float)
        ref = np.asarray(ref, dtype=float).reshape(N, self.ny)

        S_prev = self.S
        if frame is not None and S_prev is not None:
            S_prev = model.realign_states(S_prev, frame)

        P = self.scheduling.estimate(model, x0, S_prev, N)

        # warm start the QP with the shifted previous solution
        U0 = None if self.U is None else np.vstack((self.U[1:], self.U[-1:])).ravel()

        n_qp, qp_iters = 0, 0
        while True:
            U, S, iters = self.solve_qp(P, x0, ref, d, U0, W)
            n_qp += 1
            qp_iters += iters
            if n_qp >= self.scheduling.max_qp:
                break
            P_new = self.scheduling.update(model, x0, S, P)
            if P_new is None:
                break
            P, U0 = P_new, U.ravel()

        # mismatch between the scheduling used and the one of the predicted states
        P_pred = model.f_rho(model.pairs(S))

        self.S, self.P, self.U = S, P, U
        self.u_prev = U[0].copy()
        self.stats = {
            "time": time.perf_counter() - t0,
            "qp": n_qp,
            "qp_iters": qp_iters,
            "rho_error": float(np.max(np.abs(P_pred - P))),
        }
        return self.u_prev.copy()

    def predicted_outputs(self):
        # (N, ny) predicted outputs y(k+1|k), ..., y(k+N|k)
        return None if self.S is None else self.S[1:, self.out]
