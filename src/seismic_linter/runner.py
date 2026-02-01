from pathlib import Path
from typing import List, Tuple, Any, Optional
from .analyzer import analyze_path


# This standalone function runs inside the worker process
def process_file_wrapper(
    args: Tuple[Path, Optional[str], Optional[Any]],
) -> Tuple[Path, List[Any], Optional[str], Optional[str]]:
    """
    Worker function to analyze a single file.
    Args: (filepath, source_override, mapper_override)
    Returns: (file_path, violations, content_hash, error_message)
    """
    filepath, source, mapper = args
    try:
        # Use centralized logic from analyzer to avoid duplication
        violations, content_hash = analyze_path(
            filepath, source_override=source, mapper_override=mapper
        )
        return (filepath, violations, content_hash, None)

    except Exception as e:
        return (filepath, [], None, f"CRASH: {str(e)}")
