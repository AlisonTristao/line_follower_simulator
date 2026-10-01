"""
settings of a run: default values and the schema used by the configuration screen

the configuration is a dict {section: {key: value}}; the last one is saved in last_config.json
"""
import copy
import json
import os

from graphics.graphics_elements import FULL, MEDIUM, SMALL
from graphics.track_generator import LEMNISCATE, CIRCLE

LAST_CONFIG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "last_config.json")

class Field:
    """
    kind: "int" | "float" | "bool" | "choice" | "vector" (list of floats with `size` elements)
    options: list of (value, label) for "choice"
    visible: function(cfg) -> bool
    """
    def __init__(self, key, label, kind, default, help="", min=None, max=None, options=None, size=None, visible=None):
        self.key = key
        self.label = label
        self.kind = kind
        self.default = default
        self.help = help
        self.min = min
        self.max = max
        self.options = options
        self.size = size
        self.visible = visible or (lambda cfg: True)

class Section:
    def __init__(self, key, title, fields, visible=None, help=""):
        self.key = key
        self.title = title
        self.fields = fields
        self.visible = visible or (lambda cfg: True)
        self.help = help

def _is_qlpv(cfg):
    return cfg["controller"]["type"] == "qlpv"

def _is_gpc(cfg):
    return cfg["controller"]["type"] == "gpc"

def _is_iterative(cfg):
    return cfg["qlpv"]["scheduling"] == "iterative"

def _perturbation_on(cfg):
    return cfg["perturbation"]["enabled"]

SCHEDULING = [("frozen", "Frozen"), ("warm_start", "Warm start"), ("taylor", "Taylor"), ("iterative", "Iterative")]

SCHEMA = [
    Section("controller", "Controller", [
        Field("type", "Controller", "choice", "qlpv", options=[("qlpv", "NMPC qLPV"), ("gpc", "GPC (linearized)")],
              help="NMPC qLPV: QP with the qLPV model. GPC: linearized at theta = 0"),
        Field("horizon", "Prediction horizon N", "int", 45, min=2, max=200,
              help="steps of the prediction (one future point of the track for each step)"),
        Field("u_min", "Input min [%]", "float", -100, min=-100, max=100, help="lower bound of the motors input"),
        Field("u_max", "Input max [%]", "float", 100, min=-100, max=100, help="upper bound of the motors input"),
    ], help="type of controller and the common settings"),

    Section("qlpv", "NMPC qLPV", [
        Field("embedding", "qLPV embedding", "choice", "sinc",
              options=[("sinc", "sinc: rho = [cos, v sinc]"), ("sin_cos", "sin_cos: rho = [sin, cos]")],
              help="factorization of v sin(theta): sinc -> X linear in theta, sin_cos -> X linear in v"),
        Field("scheduling", "Scheduling estimation", "choice", "taylor", options=SCHEDULING,
              help="how the scheduling trajectory rho(k+j|k) is estimated"),
        Field("l_max", "Iterations l_max", "int", 3, min=1, max=50, visible=_is_iterative,
              help="maximum number of QPs per sample"),
        Field("eps", "Tolerance eps", "float", 1e-3, min=0, max=1, visible=_is_iterative,
              help="stops when ||P^(l+1) - P^l||_inf < eps"),
        Field("initial", "Initial estimate", "choice", "frozen", options=SCHEDULING[:3], visible=_is_iterative,
              help="estimate used in the first QP of the iterations"),
        Field("relaxation", "Relaxation gamma", "float", 1.0, min=0.01, max=1, visible=_is_iterative,
              help="P = P + gamma (f_rho(X) - P), gamma < 1 damps the oscillation of the fixed point"),
        Field("contouring", "Contouring error", "bool", True,
              help="position error along the track (lateral / longitudinal) instead of X / Y in the car frame"),
        Field("Q", "Q [theta, lat, lon]", "vector", [1e1, 1e4, 1e2], size=3, min=0,
              help="output weights (with contouring off: [theta, X, Y])"),
        Field("Q_N", "Q_N terminal", "vector", [1e2, 1e5, 1e3], size=3, min=0, help="weights of the last step of the horizon"),
        Field("R", "R [left, right]", "vector", [0.0, 0.0], size=2, min=0, help="weights of the inputs"),
        Field("Rd", "Rd [left, right]", "vector", [1e-2, 1e-2], size=2, min=0, help="weights of the input variation"),
        Field("disturbance_filter", "Disturbance filter", "float", 0.2, min=0, max=1,
              help="low pass of the input disturbance estimate (0 = off, 1 = no filter)"),
    ], visible=_is_qlpv, help="qLPV model predictive control"),

    Section("gpc", "GPC", [
        Field("control_horizon", "Control horizon Nu", "int", 5, min=1, max=50, help="number of future moves"),
        Field("q_theta", "Weight heading", "float", 0.5, min=0, help="weight of the heading error (divided by N)"),
        Field("q_distance", "Weight distance", "float", 1.0, min=0, help="weight of the distance error (divided by N)"),
        Field("lamb", "Weight Delta u", "float", 1e-3, min=0, help="weight of the input variation (divided by Nu)"),
        Field("theta_reference", "Heading reference", "choice", "lookahead",
              options=[("lookahead", "look-ahead: x / d0"), ("tangent", "track tangent")],
              help="reference of the heading along the horizon"),
        Field("d0", "Look-ahead d0 [m]", "float", 0.3, min=0.01, max=5, help="theta_r = x / d0"),
    ], visible=_is_gpc, help="generalized predictive control linearized at theta = 0"),

    Section("track", "Track", [
        Field("track_type", "Shape", "choice", LEMNISCATE, options=[(LEMNISCATE, "Lemniscate"), (CIRCLE, "Circle")]),
        Field("seed", "Seed", "int", 1112, min=-1, max=2 ** 31 - 1, help="random seed of the track (-1 = random)"),
        Field("track_rad", "Radius [m]", "float", 30, min=5, max=45, help="size of the track"),
        Field("noise_level", "Noise", "float", 0.225, min=0, max=1, help="random deviation of the checkpoints (fraction of the radius)"),
        Field("checkpoints", "Checkpoints", "int", 36, min=4, max=300, help="number of random checkpoints of the track"),
        Field("resolution", "Points per checkpoint", "int", 500, min=20, max=5000, help="resolution of the spline (spacing of the points)"),
        Field("track_length", "Line width [m]", "float", 0.02, min=0.002, max=0.2),
        Field("future_spacing", "Reference spacing [points]", "int", 3, min=1, max=50,
              help="track points between two steps of the reference (sets the reference speed)"),
    ], help="shape of the track and of the reference"),

    Section("car", "Car", [
        Field("wheels_radius", "Wheels radius [m]", "float", 0.04, min=0.005, max=0.5),
        Field("wheels_distance", "Wheels distance [m]", "float", 0.15, min=0.02, max=1.0),
        Field("wheels_RPM", "Max RPM", "float", 1000, min=10, max=20000, help="speed of the wheels at 100% of PWM"),
        Field("sensor_distance", "Sensor distance [m]", "float", 0.15, min=0, max=1, help="distance of the line sensor to the axle"),
        Field("sensor_count", "Sensor count", "int", 15, min=1, max=64),
        Field("sensor_spacing", "Sensor spacing [m]", "float", 0.008, min=0.001, max=0.05),
    ], help="geometry of the car"),

    Section("motors", "Motors", [
        Field("ke_l", "Gain left", "float", 1.0, min=0, max=10, help="static gain of the left motor"),
        Field("ke_r", "Gain right", "float", 1.0, min=0, max=10, help="static gain of the right motor"),
        Field("accommodation_time_l", "Settling time left [s]", "float", 0.62, min=0.01, max=10, help="5 tau of the left motor"),
        Field("accommodation_time_r", "Settling time right [s]", "float", 0.58, min=0.01, max=10, help="5 tau of the right motor"),
    ], help="first order model of the motors"),

    Section("perturbation", "Perturbation", [
        Field("enabled", "Perturbation step", "bool", False, help="applies a step on the motors (left +value, right -value)"),
        Field("time", "Step time [s]", "float", 10.0, min=0, max=3600, visible=_perturbation_on),
        Field("value", "Step value [%]", "float", 20.0, min=-100, max=100, visible=_perturbation_on),
        Field("key_step", "Keys P/O step [%]", "float", 5.0, min=0, max=100, help="change of the perturbation with the keys P / O (R resets)"),
    ], help="disturbances on the motors"),

    Section("simulation", "Simulation", [
        Field("screen_size", "Screen", "choice", FULL, options=[(FULL, "Full screen"), (MEDIUM, "Medium 1400x750"), (SMALL, "Small 800x600")]),
        Field("fps", "Sample rate [Hz]", "int", 80, min=10, max=500, help="frames per second (Ts = 1/fps)"),
        Field("real_time", "Real time", "bool", True, help="limits the simulation to the sample rate (off = as fast as possible)"),
        Field("max_time", "Max time [s]", "float", 0, min=0, max=3600, help="stops the run after this time (0 = until the end of the track)"),
    ], help="execution of the simulation"),

    Section("display", "Display", [
        Field("show_graphs", "Graphs", "bool", True),
        Field("show_fps", "FPS", "bool", True),
        Field("show_info", "Controller info", "bool", True),
        Field("show_reference", "Reference points", "bool", True),
        Field("show_prediction", "Predicted path", "bool", True),
        Field("show_minimap", "Minimap", "bool", True),
        Field("show_compass", "Compass", "bool", True),
        Field("show_coordinates", "Coordinates", "bool", True),
        Field("show_score", "Score / coverage", "bool", True),
        Field("show_sensor", "Line sensor", "bool", True),
        Field("scale", "Zoom [px/m]", "int", 300, min=50, max=1500, help="pixels per meter"),
        Field("render", "Render radius [m]", "int", 4, min=2, max=15, help="radius of the track drawn around the car"),
    ], help="what is drawn on the screen"),
]

SECTIONS = {s.key: s for s in SCHEMA}

def defaults():
    return {s.key: {f.key: copy.deepcopy(f.default) for f in s.fields} for s in SCHEMA}

def coerce(field, value):
    """
    converts and clamps a value to the field, raises ValueError if invalid
    """
    def clamp(v):
        if field.min is not None:
            v = max(field.min, v)
        if field.max is not None:
            v = min(field.max, v)
        return v

    if field.kind == "int":
        return int(clamp(int(round(float(value)))))
    if field.kind == "float":
        return float(clamp(float(value)))
    if field.kind == "bool":
        return bool(value)
    if field.kind == "choice":
        values = [o[0] for o in field.options]
        if value not in values:
            raise ValueError(f"{value} not in {values}")
        return value
    if field.kind == "vector":
        value = list(value)
        if len(value) != field.size:
            raise ValueError(f"expected {field.size} values")
        return [float(clamp(float(v))) for v in value]
    raise ValueError(field.kind)

def validate(cfg):
    """
    merges cfg with the defaults (missing / invalid values are replaced by the default)
    """
    out = defaults()
    for section in SCHEMA:
        for field in section.fields:
            try:
                out[section.key][field.key] = coerce(field, cfg.get(section.key, {}).get(field.key, field.default))
            except (ValueError, TypeError):
                pass
    return out

def load(path=LAST_CONFIG):
    try:
        with open(path) as f:
            return validate(json.load(f))
    except (OSError, ValueError):
        return defaults()

def save(cfg, path=LAST_CONFIG):
    with open(path, "w") as f:
        json.dump(cfg, f, indent=2)

def check(cfg):
    """
    errors that do not allow to run the configuration
    """
    errors = []
    if cfg["controller"]["u_min"] >= cfg["controller"]["u_max"]:
        errors.append("input min must be lower than input max")
    if cfg["controller"]["type"] == "gpc" and cfg["gpc"]["control_horizon"] > cfg["controller"]["horizon"]:
        errors.append("GPC control horizon Nu must be <= N")
    return errors

def apply_spec(cfg, spec):
    """
    controller spec used by compare_controllers.py: "gpc" | "frozen" | "warm_start" | "taylor" | "iterative",
    optionally with json arguments of the section, e.g. 'iterative:{"l_max": 5}' or 'gpc:{"d0": 0.4}'
    """
    cfg = copy.deepcopy(cfg)
    name, _, args = spec.partition(":")
    kwargs = json.loads(args) if args else {}
    if name == "gpc":
        cfg["controller"]["type"] = "gpc"
        cfg["gpc"].update(kwargs)
    else:
        cfg["controller"]["type"] = "qlpv"
        cfg["qlpv"]["scheduling"] = name
        cfg["qlpv"].update(kwargs)
    return validate(cfg)

def describe(cfg):
    # short name of the controller of the configuration
    if cfg["controller"]["type"] == "gpc":
        return f"GPC (N={cfg['controller']['horizon']}, Nu={cfg['gpc']['control_horizon']})"
    q = cfg["qlpv"]
    return f"NMPC qLPV ({q['embedding']}, {q['scheduling']}, N={cfg['controller']['horizon']})"
