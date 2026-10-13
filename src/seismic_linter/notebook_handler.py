import io
import re
import tokenize
import nbformat
from dataclasses import replace
from pathlib import Path

from typing import Dict, List, Optional, Tuple
from .rules import Violation

# A line magic (%matplotlib) or shell escape (!pip). Continuation lines that begin
# with an operator, such as "% n" or "!= 0", are plain Python and are left alone.
_LINE_MAGIC_RE = re.compile(r"^\s*(%[A-Za-z_]|!(?!=)\S)")


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


# Cell magics whose body runs as Python, as in %%time or %%capture out. Any other
# cell magic (%%bash, %%html, %%writefile, ...) makes the whole cell non-Python.
_PYTHON_CELL_MAGICS = {"time", "timeit", "capture", "prun"}

# A line magic that runs one Python statement, as in %time x = expr. Flags such as
# -n 10 are dropped and the statement is kept.
_PYTHON_LINE_MAGIC_RE = re.compile(
    r"^(\s*)%(?:time|timeit|prun)(?:\s+-[A-Za-z]+(?:\s+[\d.]+)?)*\s+(.*)$"
)


def _comment_out(line: str) -> str:
    """Comments out one physical line and keeps its indentation."""
    stripped = line.lstrip()
    indent = line[: len(line) - len(stripped)]
    return f"{indent}# {stripped}"


def _comment_line_magic(line: str) -> str:
    """
    Comment out IPython line magics (%matplotlib inline) and shell escapes
    (!pip install ...) so the rest of the cell still parses. Indentation is kept
    and the line count is unchanged, so line mapping stays valid.
    """
    if _LINE_MAGIC_RE.match(line):
        return _comment_out(line)
    return line


def _starts_statement(lines: List[str]) -> bool:
    """
    True if a new statement can begin after these lines. It cannot when they end
    inside an open bracket or after a backslash, so a line such as "%name)" in
    msg = ("first %s"
           %name)
    is part of that statement rather than a magic.
    """
    source = "\n".join(lines) + "\n"
    try:
        for _ in tokenize.generate_tokens(io.StringIO(source).readline):
            pass
    except (tokenize.TokenError, SyntaxError):
        return False
    return True


def _to_python_lines(lines: List[str]) -> List[str]:
    """
    Returns the cell lines with each line magic or shell escape commented out.
    A timing magic keeps its statement, and a backslash-continued magic also
    comments out the lines it continues, so the rest of the cell still parses.
    The line count is unchanged.
    """
    python_lines: List[str] = []
    in_magic = False  # the last commented line ends with a backslash
    for line in lines:
        if in_magic:
            python_lines.append(_comment_out(line))
            in_magic = line.rstrip().endswith("\\")
        elif _LINE_MAGIC_RE.match(line) and _starts_statement(python_lines):
            timed = _PYTHON_LINE_MAGIC_RE.match(line)
            if timed:
                python_lines.append(f"{timed.group(1)}{timed.group(2)}")
            else:
                python_lines.append(_comment_line_magic(line))
                in_magic = line.rstrip().endswith("\\")
        else:
            python_lines.append(line)
    return python_lines


def _cell_to_python(source: str) -> Optional[List[str]]:
    """
    Returns the Python lines of a code cell, or None if the cell is skipped.
    A cell magic whose body is not Python skips the cell. A cell magic that runs
    Python, such as %%time, keeps its body and only its magic line is commented.
    """
    lines = source.split("\n")
    head = next((i for i, line in enumerate(lines) if line.strip()), None)
    if head is not None and lines[head].lstrip().startswith("%%"):
        names = lines[head].lstrip()[2:].split()
        if not names or names[0] not in _PYTHON_CELL_MAGICS:
            return None
        lines[head] = _comment_out(lines[head])
    return _to_python_lines(lines)


def parse_notebook(filepath: Path) -> Tuple[str, NotebookMapper]:
    """
    Parses a Jupyter Notebook and returns:
    1. Concatenated Python source code.
    2. A mapper object to translate line numbers back to cells.

    IPython line magics and shell escapes are commented out. Cells that start
    with a cell magic whose body is not Python (%%bash, %%html, ...) are skipped.
    Cell magics that run Python (%%time, %%timeit, %%capture, %%prun) keep their
    body, and timing line magics (%time x = expr) keep their statement.
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

            # A cell magic whose body is not Python switches the whole cell.
            lines = _cell_to_python(cell_source)
            if lines is None:
                continue

            # Split into lines to track line numbers
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
