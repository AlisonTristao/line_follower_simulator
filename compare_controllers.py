"""
headless comparison of the controllers (same track and settings, from last_config.json or the defaults)

usage: python compare_controllers.py [max_time_s] [controller ...] [options]
    controller: gpc | frozen | warm_start | taylor | iterative, optionally with json arguments of the section,
                e.g. 'iterative:{"l_max": 5, "initial": "warm_start", "relaxation": 0.5}' or 'gpc:{"d0": 0.4}'
    --perturbation <time_s> <value>   applies a perturbation step during the run
    --save <folder>                   saves the data of each run (csv, see run_logger.py)
    --config <file.json>              configuration to use (default: last_config.json)
    --defaults                        uses the default configuration
    EMBEDDING=sinc|sin_cos            overrides the qLPV embedding
"""
import os
import sys
import subprocess
import json

CONTROLLERS = ["gpc", "frozen", "warm_start", "taylor", "iterative"]

def run(spec, max_time, perturbation, save, cfg_path):
    # each run is a new process (independent of the previous one)
    import config as C
    import runner

    cfg = C.defaults() if cfg_path == "defaults" else C.load(cfg_path or C.LAST_CONFIG)
    cfg = C.apply_spec(cfg, spec)
    cfg["simulation"]["max_time"] = max_time
    cfg["perturbation"]["enabled"] = perturbation is not None
    if perturbation:
        cfg["perturbation"]["time"], cfg["perturbation"]["value"] = perturbation
    if os.environ.get("EMBEDDING"):
        cfg["qlpv"]["embedding"] = os.environ["EMBEDDING"]

    result = runner.run(cfg, headless=True)
    if save:
        name = spec.replace(":", "_").translate(str.maketrans("", "", '{}" ,')).replace("_", "-")
        result.logger.save(os.path.join(save, f"{name}.csv"))
    return {"controller": result.controller, **{k: v for k, v in result.metrics.items() if k != "stop_reason"}}

def _pop_option(args, flag, n):
    if flag not in args:
        return None
    i = args.index(flag)
    values = args[i + 1:i + 1 + n]
    del args[i:i + 1 + n]
    return values

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--worker":
        spec, max_time, perturbation, save, cfg_path = sys.argv[2], float(sys.argv[3]), *map(json.loads, sys.argv[4:7])
        print(json.dumps(run(spec, max_time, perturbation, save, cfg_path)))
        sys.exit()

    args = sys.argv[1:]
    perturbation = _pop_option(args, "--perturbation", 2)
    perturbation = [float(v) for v in perturbation] if perturbation else None
    save = _pop_option(args, "--save", 1)
    save = save[0] if save else None
    cfg_path = _pop_option(args, "--config", 1)
    cfg_path = cfg_path[0] if cfg_path else None
    if "--defaults" in args:
        args.remove("--defaults")
        cfg_path = "defaults"
    max_time = float(args[0]) if args else 30
    specs = args[1:] or CONTROLLERS

    rows = []
    for spec in specs:
        out = subprocess.run([sys.executable, __file__, "--worker", spec, str(max_time),
                              json.dumps(perturbation), json.dumps(save), json.dumps(cfg_path)],
                             capture_output=True, text=True)
        line = [l for l in out.stdout.splitlines() if l.startswith("{")]
        if not line:
            print(f"{spec} failed:\n{out.stdout}\n{out.stderr}")
            continue
        rows.append(json.loads(line[-1]))

    if rows:
        keys = list(rows[0].keys())
        width = max(len(r["controller"]) for r in rows)
        print(" | ".join([f"{keys[0]:>{width}}"] + [f"{k:>14}" for k in keys[1:]]))
        for r in rows:
            cells = [f"{r[keys[0]]:>{width}}"]
            cells += [f"{r[k]:>14.3f}" if isinstance(r[k], float) else f"{str(r[k]):>14}" for k in keys[1:]]
            print(" | ".join(cells))
