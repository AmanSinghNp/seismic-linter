try:
    from importlib.metadata import version

    __version__ = version("seismic-linter")
except ImportError:
    # Fallback: try reading pyproject.toml directly if available
    try:
        from pathlib import Path
        try:
            import tomllib
        except ImportError:
            import tomli as tomllib
        
        # Look for pyproject.toml relative to this file
        # src/seismic_linter/version.py -> src/seismic_linter -> src -> root
        root = Path(__file__).resolve().parent.parent.parent
        pyproj = root / "pyproject.toml"
        if pyproj.exists():
            with open(pyproj, "rb") as f:
                data = tomllib.load(f)
            __version__ = data.get("project", {}).get("version", "0.2.0")
        else:
            # KEEP IN SYNC with pyproject.toml version
            __version__ = "0.2.0"
    except Exception:
        # KEEP IN SYNC with pyproject.toml version
        __version__ = "0.2.0"
