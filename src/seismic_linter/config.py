import sys
from pathlib import Path

try:
    import tomllib
except ImportError:
    import tomli as tomllib

from typing import Dict, Any, Optional


def _normalize_list_values(lst: Any) -> list:
    """Strip whitespace from string elements and drop empty strings."""
    if lst is None:
        return []
    if isinstance(lst, str):
        lst = [lst]
    if not isinstance(lst, (list, tuple, set)):
        return []
    has_non_string = any(not isinstance(s, str) for s in lst)
    if has_non_string:
        print(
            "Warning: Config list values must be strings; non-string entries ignored.",
            file=sys.stderr,
        )
    return [s.strip() for s in lst if isinstance(s, str) and s.strip()]


DEFAULT_CONFIG: Dict[str, Any] = {
    "include": [],
    "exclude": [".git", "__pycache__", ".venv", "venv", ".env", "build", "dist"],
    "ignore": [],
    "fail_on": ["T001", "T003"],  # Default fatal rules
}


def find_pyproject_toml(search_path: Optional[Path] = None) -> Optional[Path]:
    """
    Find pyproject.toml in current or parent directories.
    Starts looking from search_path if provided, else CWD.
    When search_path is None, search starts from the current working directory;
    ensure CWD is set appropriately in non-interactive environments.
    """
    current = (search_path or Path.cwd()).resolve()

    # Check if current is file, get parent
    if current.is_file():
        current = current.parent

    for parent in [current, *current.parents]:
        config_file = parent / "pyproject.toml"
        if config_file.exists():
            return config_file
    return None


def load_config(search_path: Optional[Path] = None) -> Dict[str, Any]:
    """
    Load config from pyproject.toml, merging with defaults.
    """
    config_path = find_pyproject_toml(search_path)
    user_config: Dict[str, Any] = {}

    if config_path:
        try:
            with open(config_path, "rb") as f:
                pyproject = tomllib.load(f)

            tool_config = pyproject.get("tool", {}).get("seismic-linter", {})
            user_config = tool_config

        except Exception as e:
            print(f"Warning: Failed to parse {config_path}: {e}", file=sys.stderr)

    # Merge: Defaults < User Config
    final_config = DEFAULT_CONFIG.copy()

    # Normalize hyphenated key to underscore before processing
    if "fail-on" in user_config:
        user_config["fail_on"] = user_config.pop("fail-on")

    # Update non-list keys via update
    for k, v in user_config.items():
        if k not in ["include", "exclude", "ignore", "fail_on"]:
            final_config[k] = v

    # Smart Merge for Lists
    # Exclude/Ignore: Additive (Default + User)
    for list_key in ["exclude", "ignore"]:
        user_val = user_config.get(list_key, [])
        if isinstance(user_val, str):
            user_val = [user_val]
        if not isinstance(user_val, list):
            user_val = []

        default_val = final_config.get(list_key, [])
        # Merge unique; strip and drop empty
        merged = list(set(default_val) | set(user_val))
        final_config[list_key] = sorted(_normalize_list_values(merged))

    # Include/Fail_on: Replacement (User overrides Default)
    # If user specifies include, they likely want ONLY those.
    # If user specifies fail_on, they likely want ONLY those.
    for replace_key in ["include", "fail_on"]:
        if replace_key in user_config:
            final_config[replace_key] = user_config[replace_key]

    # Re-run coercion to ensure final types (legacy check); strip list values
    for key in ["include", "exclude", "ignore", "fail_on"]:
        val = final_config.get(key)
        if val is not None:
            if isinstance(val, str):
                final_config[key] = _normalize_list_values([val])
            elif not isinstance(val, (list, tuple, set)):
                # fallback/warn
                msg = (
                    f"Warning: Config key '{key}' expected list, got {type(val)}. "
                    "Ignoring."
                )
                print(msg, file=sys.stderr)
                final_config[key] = []
            else:
                final_config[key] = _normalize_list_values(list(val))

    return final_config
