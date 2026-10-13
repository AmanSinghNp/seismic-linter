import nbformat
from dataclasses import replace
from pathlib import Path

from typing import Dict, List, Optional, Tuple
from .rules import Violation


class NotebookMapper:
    def __init__(self) -> None:
        # virtual_line -> (cell_index, local_line)
        self.virtual_lines: Dict[int, Tuple[int, int]] = {}
        self.cells: Dict[int, str] = {}  # cell_index -> cell_source

    def map_line(self, virtual_line: int) -> Tuple[Optional[int], int]:
        """
        Map virtual line to (cell_index, local_line).
        If not in map (e.g. synthetic), returns (None, virtual_line) as fallback.
        """
        return self.virtual_lines.get(virtual_line, (None, virtual_line))


# Violation typed as Any to avoid circular import with rules.py.
def map_violations(
    violations: List[Violation], mapper: NotebookMapper
) -> List[Violation]:
    """
    Maps violations from synthetic source back to notebook cells.
    Returns a new list of new Violation instances (does not mutate input).
    """
    mapped = []
    for v in violations:
        cell_idx, local_line = mapper.map_line(v.lineno)
        if cell_idx is not None:
            new_v = replace(v, cell_id=cell_idx + 1, lineno=local_line)
            mapped.append(new_v)
        else:
            new_v = replace(v, cell_id=None)
            mapped.append(new_v)
    return mapped


def _comment_line_magic(line: str) -> str:
    """
    Comment out IPython line magics (%matplotlib inline) and shell escapes
    (!pip install ...) so the rest of the cell still parses. Indentation is kept
    and the line count is unchanged, so line mapping stays valid.
    """
    stripped = line.lstrip()
    if stripped.startswith(("%", "!")):
        indent = line[: len(line) - len(stripped)]
        return f"{indent}# {stripped}"
    return line


def parse_notebook(filepath: Path) -> Tuple[str, NotebookMapper]:
    """
    Parses a Jupyter Notebook and returns:
    1. Concatenated Python source code.
    2. A mapper object to translate line numbers back to cells.

    IPython line magics and shell escapes are commented out. Cells that start
    with a cell magic (%%bash, %%html, ...) are skipped, since their body is not
    Python.
    """
    with open(filepath, "r", encoding="utf-8") as f:
        nb = nbformat.read(f, as_version=4)

    source_lines = []
    mapper = NotebookMapper()

    current_line = 1

    # For now stick to raw content (no implicit imports).

    for i, cell in enumerate(nb.cells):
        if cell.cell_type == "code":
            cell_source = cell.source

            # Normalize source if it's a list (nbformat 4 allows list of strings)
            if isinstance(cell_source, list):
                cell_source = "".join(cell_source)

            if not cell_source:
                continue

            # A cell magic switches the whole cell to another language.
            if cell_source.lstrip().startswith("%%"):
                continue

            # Split into lines to track line numbers
            lines = [_comment_line_magic(line) for line in cell_source.split("\n")]
            mapper.cells[i] = cell_source

            # Add to concatenated source; strict line mapping maps back to cells.
            # To keep line numbers clean, we just append lines.

            for local_idx, line in enumerate(lines):
                source_lines.append(line)
                mapper.virtual_lines[current_line] = (i, local_idx + 1)
                current_line += 1

            # Add a newline between cells to avoid syntax errors like `a=1b=2`
            source_lines.append("")
            # Blank line maps to end of cell i; violations get cell_id = i+1.
            mapper.virtual_lines[current_line] = (i, len(lines) + 1)
            current_line += 1

    full_source = "\n".join(source_lines)
    return full_source, mapper
