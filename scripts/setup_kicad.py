"""Initialize the project-local KiCad profile once, without changing later preferences."""
import json
import os
from pathlib import Path

profile = Path(os.environ["KICAD_CONFIG_HOME"]) / "10.0"
profile.mkdir(parents=True, exist_ok=True)
config = profile / "kicad_common.json"
if not config.exists():
    # Exclusive creation avoids overwriting preferences in concurrent launches.
    try:
        with config.open("x") as stream:
            json.dump({"api": {"enable_server": True}}, stream, indent=2)
    except FileExistsError:
        pass
