"""
Command-line interface for seismic-linter.
"""

import argparse
import sys
import multiprocessing
import fnmatch
import concurrent.futures
import json
from dataclasses import asdict
from pathlib import Path
from typing import List, Dict, Any, Optional, Set

# Import from package
from . import __version__
from .caching import ContentCache
from .runner import process_file_wrapper
from .config import load_config, find_pyproject_toml, _normalize_list_values
from .rules import Violation
from .notebook_handler import parse_notebook


SUPPORTED_EXTENSIONS = {".py", ".ipynb"}


def is_excluded(
    path: Path, exclude_patterns: List[str], base_path: Optional[Path] = None
) -> bool:
    """Check if path matches any exclude pattern."""
    # Normalize to forward slashes for consistent glob matching
    path_str = str(path).replace("\\", "/")
    name = path.name

    # Check relative path if base_path is provided
    rel_path_str = None
    if base_path:
        try:
            rel_path_str = str(path.relative_to(base_path)).replace("\\", "/")
        except ValueError:
            pass

    # Use resolved parts to match against directory names in patterns
    # e.g. path="project/.git/config" parts=("project", ".git", "config")
    # if ".git" is in patterns, we should match.
    # Note: patterns might be globs too.

    path_parts = set(part for part in path.parts)

    for pattern in exclude_patterns:
        # 1. Exact Name/Basename Match (e.g. pattern=".git" matches name=".git")
        if fnmatch.fnmatch(name, pattern):
            return True

        # 2. Path segment match: .git in subdir/.git/file
        # Simple name, no slash: treat as directory exclude
        if "/" not in pattern and "\\" not in pattern:
            if pattern in path_parts:
                return True

        # 3. Full Path Globs
        if fnmatch.fnmatch(path_str, pattern):
            return True
        if rel_path_str and fnmatch.fnmatch(rel_path_str, pattern):
            return True

    return False


def collect_files(base_path: Path, config: Dict[str, Any]) -> List[Path]:
    """
    Collects files based on config 'include' patterns (or defaults),
    then filters by extension and 'exclude' patterns.
    """
    files_to_scan = set()

    # 1. Determine base patterns (Default to all if no 'include' in config)
    includes = config.get("include", [])

    candidates = []
    if not includes:
        if base_path.is_dir():
            candidates.extend(base_path.rglob("*"))
        else:
            candidates.append(base_path)
    else:
        if base_path.is_file():
            candidates.append(base_path)
        else:
            for pattern in includes:
                # If pattern contains glob characters
                if any(c in pattern for c in "*?[]"):
                    candidates.extend(base_path.glob(pattern))
                else:
                    # It's a directory or file name
                    p = base_path / pattern
                    if p.is_dir():
                        candidates.extend(p.rglob("*"))
                    elif p.exists():
                        candidates.append(p)

    # 2. Filter Candidates
    excludes = config.get("exclude", [])

    for file_path in candidates:
        file_path = Path(file_path)

        if not file_path.is_file():
            continue

        if file_path.suffix not in SUPPORTED_EXTENSIONS:
            continue

        if is_excluded(file_path, excludes, base_path):
            continue

        files_to_scan.add(file_path)

    return sorted(list(files_to_scan))


def main():
    parser = argparse.ArgumentParser(
        prog="seismic-linter",
        description="Detect temporal causality violations in seismic ML code",
    )
    parser.add_argument(
        "path",
        type=Path,
        nargs="*",
        default=None,
        help="File(s) or directory to analyze (default: current directory). Note: Config is loaded from the first path.",
    )
    parser.add_argument(
        "--ignore", nargs="+", help="List of rule IDs to ignore (overrides config)"
    )
    parser.add_argument(
        "--fail-on",
        nargs="+",
        help="List of rule IDs to treat as fatal errors (overrides config)",
    )
    parser.add_argument(
        "--output",
        choices=["text", "json", "github"],
        default="text",
        help="Output format (default: text)",
    )
    parser.add_argument(
        "--no-fail-on-error",
        action="store_true",
        help="Do not exit with non-zero code even if errors are found",
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )

    args = parser.parse_args()

    # Resolve paths: none or empty -> cwd; else use given paths
    if args.path is None or len(args.path) == 0:
        paths_to_scan = [Path.cwd()]
    else:
        paths_to_scan = [Path(p).resolve() for p in args.path]

    for p in paths_to_scan:
        if not p.exists():
            print(f"Error: Path '{p}' does not exist.", file=sys.stderr)
            sys.exit(1)

    # Load config and project root from first path
    scan_path = paths_to_scan[0]
    config = load_config(scan_path)
    pyproj = find_pyproject_toml(scan_path)
    if pyproj:
        project_root = pyproj.parent
    else:
        project_root = scan_path if scan_path.is_dir() else scan_path.parent

    # Override config with CLI args (normalize to match rule IDs)
    if args.ignore:
        config["ignore"] = _normalize_list_values(args.ignore)
    if args.fail_on:
        config["fail_on"] = _normalize_list_values(args.fail_on)

    violations_by_file: Dict[str, List[Violation]] = {}

    # Collect files from all paths (merge and dedupe)
    excludes = config.get("exclude", [])
    all_files: Set[Path] = set()
    for p in paths_to_scan:
        if p.is_file():
            if p.suffix in SUPPORTED_EXTENSIONS and not is_excluded(p, excludes, p.parent):
                all_files.add(p)
        else:
            all_files.update(collect_files(p, config))
    files_to_analyze = sorted(all_files)

    if not files_to_analyze:
        print("\n=== Seismic Linter Scan ===\n")
        print("No Python or Jupyter files to analyze.")
        sys.exit(0)

    # Initialize Cache
    cache = ContentCache(project_root)

    files_to_worker = []

    # Phase 1: Check Cache Local (simple files + notebooks)
    # We also prepare args for the worker to avoid re-reading/re-parsing
    worker_args = []

    for f in files_to_analyze:
        # We check cache locally to avoid spinning up workers for unchanged files.
        # For .ipynb we parse to get source; avoids worker overhead if cached.
        
        source: Optional[str] = None
        mapper: Optional[Any] = None
        
        try:
            if f.suffix == ".py":
                with open(f, "r", encoding="utf-8") as file_obj:
                    source = file_obj.read()
            elif f.suffix == ".ipynb":
                # Parsing is needed to get canonical source for hash
                source, mapper = parse_notebook(f)

            if source:
                h = ContentCache.compute_hash(source)
                cached = cache.get(f, h)
                if cached is not None:
                    violations_by_file[str(f)] = cached
                    continue
        except Exception as e:
            print(f"Cache skip (read/parse error): {f}: {e}", file=sys.stderr)
            # If read failed, we might still let the worker try and fail gracefully
            # But usually we just pass what we have. If source is None, worker will try read.
            pass

        # If not cached, add to worker args.
        # Pass source and mapper so worker doesn't need to re-read/re-parse.
        worker_args.append((f, source, mapper))

    # Phase 2: Workers
    if worker_args:
        cpu_count = multiprocessing.cpu_count()
        workers = min(cpu_count, len(worker_args))

        with concurrent.futures.ProcessPoolExecutor(max_workers=workers) as executor:
            # map expects a single iterable of arguments
            results = executor.map(process_file_wrapper, worker_args)

            for file_path, new_violations, content_hash, error in results:
                if error:
                    # Surface error to user
                    print(f"Error analyzing {file_path}: {error}", file=sys.stderr)
                    # Create a synthetic violation so it shows in report too
                    err_violation = Violation(
                        rule_id="E000",
                        message=f"Analysis failed: {error}",
                        filename=str(file_path),
                        lineno=0,
                        col_offset=0,
                        severity="error",
                    )
                    violations_by_file[str(file_path)] = [err_violation]
                else:
                    violations_by_file[str(file_path)] = new_violations
                    if content_hash:
                        cache.set(file_path, content_hash, new_violations)

    ignored_rules = set(config.get("ignore", []))
    fatal_rules = set(config.get("fail_on", []))

    # Flatten results
    all_violations = []
    has_error = False

    for filepath, violations in violations_by_file.items():
        active_violations = [v for v in violations if v.rule_id not in ignored_rules]

        for v in active_violations:
            is_fatal = v.rule_id in fatal_rules
            if v.severity == "error" or is_fatal:
                has_error = True
            all_violations.append(v)

    # Output selection
    if args.output == "json":
        print_json(all_violations)
    elif args.output == "github":
        print_github(all_violations, fatal_rules)
    else:
        print_text(violations_by_file, ignored_rules, fatal_rules)

    # Exit Code Logic
    if args.no_fail_on_error:
        sys.exit(0)
    else:
        sys.exit(1 if has_error else 0)


def print_text(
    violations_by_file: Dict[str, List[Violation]],
    ignored_rules: Set[str],
    fatal_rules: Set[str],
):
    print("\n=== Seismic Linter Scan ===\n")
    total_violations = 0

    for filepath, violations in violations_by_file.items():
        active_violations = [v for v in violations if v.rule_id not in ignored_rules]

        if not active_violations:
            continue

        print(f"File: {filepath}")
        for v in active_violations:
            total_violations += 1
            is_fatal = v.rule_id in fatal_rules

            icon = "⚠️"
            if v.severity == "error" or is_fatal:
                icon = "❌"
            elif v.severity == "warning":
                icon = "⚠️"
            else:
                icon = "ℹ️"

            location = f"Line {v.lineno}"
            if v.cell_id:
                location = f"Cell {v.cell_id}, Line {v.lineno}"

            print(f"  {icon} [{location}] {v.rule_id}: {v.message}")
            if v.context:
                print(f"     Context: {v.context}")
        print("")

    if total_violations == 0:
        print("✅ No violations found.")
    else:
        print(f"Found {total_violations} potential violation(s).")


def print_json(violations: List[Violation]):
    output = []
    for v in violations:
        v_dict = asdict(v)
        output.append(v_dict)
    print(json.dumps(output, indent=2))


def print_github(violations: List[Violation], fatal_rules: Set[str]):
    # Format: ::severity file={name},line={line}::{message}
    # Severity levels: debug, notice, warning, error
    current_dir = Path.cwd()
    for v in violations:
        severity = "warning"
        if v.severity == "error" or v.rule_id in fatal_rules:
            severity = "error"
        elif v.severity == "info":
            severity = "notice"

        message = f"{v.rule_id}: {v.message}"
        if v.cell_id:
            message = f"[Cell {v.cell_id}] {message}"

        # Try to make path relative to CWD for better GitHub UI integration
        display_path = v.filename
        try:
            display_path = str(Path(v.filename).relative_to(current_dir))
        except ValueError:
            pass

        print(f"::{severity} file={display_path},line={v.lineno}::{message}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted by user. Exiting.", file=sys.stderr)
        sys.exit(130)  # Standard SIGINT exit code
