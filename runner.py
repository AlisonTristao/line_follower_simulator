"""
runs one simulation from a configuration (see config.py) and collects the data of the run
"""
import os
# small matrices: multithreaded BLAS only adds overhead
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

import time
from dataclasses import dataclass, field

import numpy as np

import simulator as S
import config as C
from mpc import LineFollowerQLPV, LineFollowerController, LineFollowerGPC
from run_logger import RunLogger

def make_controller(cfg):
    ctrl, car, motors = cfg["controller"], cfg["car"], cfg["motors"]
    Ts = 1 / cfg["simulation"]["fps"]
    params = (Ts, car["wheels_radius"], car["wheels_distance"], car["wheels_RPM"], motors["ke_l"], motors["ke_r"],
              motors["accommodation_time_l"], motors["accommodation_time_r"])

    if ctrl["type"] == "gpc":
        g = cfg["gpc"]
        return LineFollowerGPC(*params, horizon=ctrl["horizon"], control_horizon=g["control_horizon"],
                               q_theta=g["q_theta"], q_distance=g["q_distance"], lamb=g["lamb"], d0=g["d0"],
                               theta_reference=g["theta_reference"], u_min=ctrl["u_min"], u_max=ctrl["u_max"])

    q = cfg["qlpv"]
    kwargs = {}
    if q["scheduling"] == "iterative":
        kwargs = {"l_max": q["l_max"], "eps": q["eps"], "initial": q["initial"], "relaxation": q["relaxation"]}
    model = LineFollowerQLPV(*params, embedding=q["embedding"])
    return LineFollowerController(model, ctrl["horizon"], q["Q"], q["R"], q["Rd"], q["Q_N"], ctrl["u_min"], ctrl["u_max"],
                                  q["scheduling"], disturbance_filter=q["disturbance_filter"], contouring=q["contouring"], **kwargs)

@dataclass
class RunResult:
    cfg: dict
    controller: str
    logger: RunLogger
    stop_reason: str
    metrics: dict = field(default_factory=dict)
    track: tuple = None

def metrics(logger, stop_reason, fps):
    rows = logger.rows
    if not rows:
        return {}
    col = lambda k: np.array([r[k] for r in rows], dtype=float)
    lat = np.abs(col("lateral_error"))
    solve = col("solve_time_ms")
    return {
        "finished": stop_reason == "finished",
        "stop_reason": stop_reason,
        "time_s": len(rows) / fps,
        "coverage_%": 100.0 if stop_reason == "finished" else float(rows[-1]["coverage"]),
        "lat_rms_cm": float(np.sqrt(np.mean(lat ** 2)) * 100),
        "lat_max_cm": float(lat.max() * 100),
        "speed_mean_m_s": float(np.mean(col("speed"))),
        "solve_mean_ms": float(np.mean(solve)),
        "solve_max_ms": float(np.max(solve)),
        "qp_mean": float(np.mean(col("qp"))),
        "rho_err_mean": float(np.mean(col("rho_error"))),
    }

def log_step(logger, data, u, controller):
    """
    one row of the run: time, car pose (track coordinates), inputs, errors,
    reference / prediction at k+1 and k+N (car frame of k), scheduling and solver
    """
    x, y, heading = S.get_car_pose()
    ref, pred, stats = controller.ref, controller.prediction(), controller.stats
    P = controller.scheduling_trajectory()
    logger.log(
        t=S.get_time(), x=x, y=y, heading=heading,
        speed=data.speed, omega=data.omega, w_l=data.wheels_speed[0], w_r=data.wheels_speed[1],
        u_l=u[0], u_r=u[1], perturbation=S.get_perturbation(),
        lateral_error=data.lateral_error, coverage=S.get_coverage(),
        theta_ref_1=ref[0, 0], X_ref_1=ref[0, 1], Y_ref_1=ref[0, 2],
        theta_pred_1=pred[0, 0], X_pred_1=pred[0, 1], Y_pred_1=pred[0, 2],
        theta_ref_N=ref[-1, 0], X_ref_N=ref[-1, 1], Y_ref_N=ref[-1, 2],
        theta_pred_N=pred[-1, 0], X_pred_N=pred[-1, 1], Y_pred_N=pred[-1, 2],
        rho1_N=np.nan if P is None else P[-1, 0], rho2_N=np.nan if P is None else P[-1, 1],
        solve_time_ms=stats["time"] * 1e3, qp=stats["qp"], qp_iters=stats["qp_iters"], rho_error=stats["rho_error"],
    )

def _setup_graphs(controller, cfg):
    S.add_graph("theta [deg]", ["ref", "pred"], (-90, 90))
    S.add_graph("X [cm]", ["ref", "pred"], (-30, 30))
    if isinstance(controller, LineFollowerController):
        S.add_graph("rho", ["rho_1", "rho_2"], (-1, 1) if cfg["qlpv"]["embedding"] == "sin_cos" else (-1, 5))
    S.add_graph("solver [ms]", ["time"], (0, 25))
    S.add_graph("lateral error [cm]", ["e"], (-5, 5))

def _update_graphs(controller, data, is_qlpv):
    ref, pred, P = controller.ref, controller.prediction(), controller.scheduling_trajectory()
    stats = controller.stats
    S.set_graph_data("theta [deg]", "ref", np.degrees(ref[:, 0]))
    S.set_graph_data("theta [deg]", "pred", np.degrees(pred[:, 0]))
    S.set_graph_data("X [cm]", "ref", ref[:, 1] * 100)
    S.set_graph_data("X [cm]", "pred", pred[:, 1] * 100)
    if P is not None:
        S.set_graph_data("rho", "rho_1", P[:, 0])
        S.set_graph_data("rho", "rho_2", P[:, 1])
    S.push_graph_data("solver [ms]", "time", stats["time"] * 1e3)
    S.push_graph_data("lateral error [cm]", "e", data.lateral_error * 100)
    S.set_predicted_path(pred[:, 1:])
    S.set_info(f"{controller.name} | " + (f"QPs: {stats['qp']} | " if is_qlpv else "") + f"{stats['time']*1e3:.2f} ms")

def run(cfg, headless=False, screen_size=None):
    """
    runs the simulation of the configuration; the data stays in memory (result.logger.save() writes the csv)
    """
    sim, track, car, motors, disp, pert = (cfg[k] for k in ("simulation", "track", "car", "motors", "display", "perturbation"))
    fps = sim["fps"]

    S.reset_simulation()
    S.start_simulation(screen_size or sim["screen_size"], fps, scale=disp["scale"], render=disp["render"],
                       seed=None if track["seed"] < 0 else track["seed"], track_type=track["track_type"],
                       track_length=track["track_length"], sensor_spacing=car["sensor_spacing"],
                       headless=headless, real_time=sim["real_time"] and not headless,
                       display={k: v for k, v in disp.items() if k.startswith("show_")},
                       track={**{k: track[k] for k in ("noise_level", "checkpoints", "resolution", "track_rad")},
                              "file": C.track_path(track["file"]), "spacing": track["file_spacing"]},
                       perturbation_key_step=pert["key_step"])
    S.set_car_dynamics(car["wheels_radius"], car["wheels_distance"], car["wheels_RPM"], motors["ke_l"], motors["ke_r"],
                       motors["accommodation_time_l"], motors["accommodation_time_r"], car["sensor_distance"], car["sensor_count"])
    S.set_future_points(cfg["controller"]["horizon"], track["future_spacing"])

    controller = make_controller(cfg)
    is_qlpv = isinstance(controller, LineFollowerController)
    logger = RunLogger(name=cfg["controller"]["type"] if not is_qlpv else cfg["qlpv"]["scheduling"],
                       meta={"controller": controller.name, "config": cfg, "date": time.strftime("%Y-%m-%d %H:%M:%S")})
    logger.set_track(*S.get_track())

    if not headless:
        _setup_graphs(controller, cfg)

    max_steps = int(sim["max_time"] * fps) if sim["max_time"] > 0 else None
    step_time = int(pert["time"] * fps) if pert["enabled"] else None

    u = np.zeros(2)
    k = 0
    reason = None
    while True:
        if max_steps is not None and k >= max_steps:
            reason = "time"
            break
        if step_time is not None and k == step_time:
            S.set_perturbation(pert["value"])

        data = S.step_simulation(*u)
        if data is None:
            reason = S.stop_reason
            break

        u = controller.step(data.wheels_speed, data.future_points)
        log_step(logger, data, u, controller)
        if not headless:
            _update_graphs(controller, data, is_qlpv)
        k += 1

    return RunResult(cfg, controller.name, logger, reason, metrics(logger, reason, fps), S.get_track())
