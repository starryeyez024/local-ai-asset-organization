"""Shared configuration for the linker and Explorer generator."""

from pathlib import Path
import tomllib


def default_config_path(home=None):
    home = Path(home) if home is not None else Path.home()
    preferred = home / ".config/agent-tools/agent-config.toml"
    legacy = home / ".config/ai-tools/ai-tools.toml"
    return preferred if preferred.exists() or not legacy.exists() else legacy


def read_directories(config_path=None):
    path = Path(config_path).expanduser() if config_path is not None else default_config_path()
    try:
        with path.open("rb") as source:
            directories = tomllib.load(source).get("directories", {})
    except (OSError, tomllib.TOMLDecodeError) as error:
        raise ValueError(f"Cannot read configuration {path}: {error}") from error
    if not isinstance(directories, dict):
        raise ValueError(f"Expected a [directories] table in {path}")
    result = {}
    for key in ("install_dir", "symlinks_dir"):
        value = directories.get(key)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"Missing [directories].{key} in {path}")
        directory = Path(value).expanduser()
        if not directory.is_absolute():
            raise ValueError(f"[directories].{key} must be an absolute path in {path}")
        result[key] = str(directory)
    return result
