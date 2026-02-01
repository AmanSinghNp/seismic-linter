try:
    from importlib.metadata import version, PackageNotFoundError
except ImportError:
    from importlib_metadata import version, PackageNotFoundError  # type: ignore

def _get_version():
    try:
        return version("seismic-linter")
    except (ImportError, PackageNotFoundError):
        pass

    # Fallback: try reading pyproject.toml directly if available
    try:
        from pathlib import Path

        try:
            import tomllib
        except ImportError:
            try:
                import tomli as tomllib
            except ImportError:
                return "0.2.0"  # Fallback if no toml parser

        # Look for pyproject.toml relative to this file
        # src/seismic_linter/version.py -> src/seismic_linter -> src -> root
        root = Path(__file__).resolve().parent.parent.parent
        pyproj = root / "pyproject.toml"
        if pyproj.exists():
            with open(pyproj, "rb") as f:
                data = tomllib.load(f)
            return data.get("project", {}).get("version", "0.2.0")
    except Exception:
        pass
        
    return "0.2.0"

__version__ = _get_version()

