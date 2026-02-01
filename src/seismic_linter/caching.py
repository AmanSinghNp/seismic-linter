import hashlib
import json
import sys
from pathlib import Path
from typing import List, Optional
from dataclasses import asdict
from .version import __version__ as LINTER_VERSION
from .rules import Violation

CACHE_DIR_NAME = ".seismic_cache"


class ContentCache:
    def __init__(self, root_path: Path):
        self.cache_dir = root_path / CACHE_DIR_NAME
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_cache_path(self, filepath: Path) -> Path:
        """
        Get the path to the cache file for a specific source file.
        Cache key is absolute path; not portable across machines/directories.
        """
        # We hash the absolute path to avoid collisions
        path_hash = hashlib.md5(str(filepath.resolve()).encode("utf-8")).hexdigest()
        return self.cache_dir / f"{path_hash}.json"

    @staticmethod
    def compute_hash(content: str) -> str:
        return hashlib.md5(content.encode("utf-8")).hexdigest()

    def get(self, filepath: Path, content_hash: str) -> Optional[List[Violation]]:
        """
        Retrieve violations from cache if valid.
        Cache entries from future linter versions or with changed Violation structure
        are treated as miss; new optional Violation fields should be read with .get().
        """
        cache_path = self._get_cache_path(filepath)
        if not cache_path.exists():
            return None

        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Verify validity
            if data.get("linter_version") != LINTER_VERSION:
                return None
            if data.get("content_hash") != content_hash:
                return None

            # Reconstruct Violations
            violations = []
            for v_data in data.get("violations", []):
                # Handle cell_id optionally
                cell_id = v_data.get("cell_id")

                v = Violation(
                    rule_id=v_data["rule_id"],
                    message=v_data["message"],
                    filename=v_data["filename"],  # usually current file
                    lineno=v_data["lineno"],
                    col_offset=v_data["col_offset"],
                    severity=v_data["severity"],
                    context=v_data.get("context"),
                    cell_id=cell_id,
                )
                violations.append(v)
            return violations

        except Exception:
            # On any error (corrupt file, etc), treat as cache miss
            return None

    def set(
        self,
        filepath: Path,
        content_hash: str,
        violations: List[Violation],
    ) -> None:
        """
        Save violations to cache.
        """
        cache_path = self._get_cache_path(filepath)
        data = {
            "file_path": str(filepath),
            "content_hash": content_hash,
            "linter_version": LINTER_VERSION,
            "violations": [asdict(v) for v in violations],
        }

        try:
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(data, f)
        except Exception as e:
            print(f"Warning: Failed to write cache: {e}", file=sys.stderr)
