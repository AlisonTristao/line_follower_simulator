"""
scheduling trajectory estimation P_k = col(rho(k), rho(k+1|k), ..., rho(k+N-1|k))

the scheduling proxy is evaluated on z(j) = [x(j), x(j+1)] (see model.f_rho), so rho(k+j|k) needs
an estimate of the state sequence x(k), ..., x(k+N).

every strategy receives the information of the instant k already written in the current frame:
    model   qLPV model (pairs, f_rho, jacobian_rho, saturate_rho)
    x0      measured state x(k)
    S_prev  previous predicted states (x(k-1|k-1), x(k|k-1), ..., x(k-1+N|k-1)), shape (N+1, nx), or None
    N       prediction horizon
"""
import numpy as np

def previous_sequence(x0, S_prev, N):
    # (x(k), x*(k+1|k-1), ..., x*(k+N-1|k-1), x*(k+N-1|k-1)): measured state + shifted previous prediction
    return np.vstack((x0, S_prev[2:N + 1], S_prev[N:N + 1]))

class Scheduling:
    name = "base"
    # number of QPs per sample (> 1 only for the iterative strategy)
    max_qp = 1

    def estimate(self, model, x0, S_prev, N):
        raise NotImplementedError

    def update(self, model, x0, S, P):
        """
        called after each QP: returns a new estimate or None to stop (only used by the iterative strategy)
        """
        return None

    def __repr__(self):
        return self.name

class Frozen(Scheduling):
    """
    rho(k+j|k) = f_rho(x(k), x(k)) for all j (the current state is kept along the horizon)
    """
    name = "frozen"

    def estimate(self, model, x0, S_prev, N):
        return np.tile(model.f_rho(np.concatenate((x0, x0))), (N, 1))

class WarmStart(Scheduling):
    """
    rho(k+j|k) = f_rho(x*(k+j|k-1), x*(k+j+1|k-1)), using the previous optimal state trajectory
    (x(k) is the measured state and the last state is repeated)
    """
    name = "warm_start"

    def estimate(self, model, x0, S_prev, N):
        if S_prev is None:
            return Frozen().estimate(model, x0, S_prev, N)
        return model.f_rho(model.pairs(previous_sequence(x0, S_prev, N)))

class Taylor(Scheduling):
    """
    recursive first order extrapolation around the current point z(k):

        rho(k|k)   = f_rho(z(k)),  sigma_k = d f_rho/dz at z(k)
        rho(k+j|k) = sat(rho(k+j-1|k) + sigma_k (z(k+j) - z(k+j-1)))

    with the increments from the previous optimal state trajectory (one f_rho evaluation,
    one jacobian and N-1 matrix-vector products).
    """
    name = "taylor"

    def estimate(self, model, x0, S_prev, N):
        if S_prev is None:
            return Frozen().estimate(model, x0, S_prev, N)
        Z = model.pairs(previous_sequence(x0, S_prev, N))
        sigma = model.jacobian_rho(Z[0])
        dZ = np.diff(Z, axis=0) @ sigma.T
        P = np.empty((N, model.nrho))
        P[0] = model.f_rho(Z[0])
        for j in range(1, N):
            P[j] = model.saturate_rho(P[j - 1] + dZ[j - 1])
        return P

class Iterative(Scheduling):
    """
    P^0 from the initial strategy (frozen by default), then the QP is solved again with

        P^{l+1} = P^l + gamma (f_rho(z^l(k)), ..., f_rho(z^l(k+N-1))) - P^l),  z^l(j) = [x^l(j|k), x^l(j+1|k)]

    until ||P^{l+1} - P^l||_inf < eps or l_max QPs. gamma = 1 is the plain fixed point iteration,
    gamma < 1 damps the oscillation of the fixed point.
    """
    name = "iterative"

    def __init__(self, l_max=3, eps=1e-3, initial="frozen", relaxation=1.0):
        self.max_qp = l_max
        self.eps = eps
        self.relaxation = relaxation
        self.initial = make_scheduling(initial)
        self.name = f"iterative({self.initial.name}, l_max={l_max}, gamma={relaxation:g})"

    def estimate(self, model, x0, S_prev, N):
        return self.initial.estimate(model, x0, S_prev, N)

    def update(self, model, x0, S, P):
        step = model.f_rho(model.pairs(S)) - P
        if np.max(np.abs(step)) < self.eps:
            return None
        return model.saturate_rho(P + self.relaxation * step)

STRATEGIES = {
    "frozen": Frozen,
    "warm_start": WarmStart,
    "taylor": Taylor,
    "iterative": Iterative,
}

def make_scheduling(name, **kwargs):
    if isinstance(name, Scheduling):
        return name
    if name not in STRATEGIES:
        raise ValueError(f"unknown scheduling strategy '{name}', options: {list(STRATEGIES)}")
    return STRATEGIES[name](**kwargs)
