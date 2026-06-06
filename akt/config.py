"""Read/write the AKT config file (simple `key: value` lines)."""
import os
import re
from pathlib import Path

DEFAULT_CONFIG = Path.home() / ".claude" / "akt-config.md"
_LINE = re.compile(r"^([a-z_]+):\s*(.*)$")


def config_path():
    return Path(os.environ.get("AKT_CONFIG", str(DEFAULT_CONFIG)))


def read_config(path=None):
    path = Path(path) if path else config_path()
    cfg = {}
    if not path.exists():
        return cfg
    for line in path.read_text().splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        m = _LINE.match(stripped)
        if m:
            cfg[m.group(1)] = m.group(2).strip()
    return cfg


def write_config(cfg, path=None):
    path = Path(path) if path else config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["{}: {}".format(k, v) for k, v in sorted(cfg.items())]
    path.write_text("\n".join(lines) + "\n")


def get(key, path=None):
    return read_config(path).get(key)


def set_value(key, value, path=None):
    cfg = read_config(path)
    cfg[key] = value
    write_config(cfg, path)
