# Contributing to seismic-linter

Thank you for your interest in contributing! 🎉

## How to Contribute

### Reporting Bugs
- Use GitHub Issues
- Include minimal reproducible example
- Specify Python version and OS

### Suggesting Features
- Check existing issues first
- Describe the problem it solves
- Propose implementation approach

### Code Contributions

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests for new functionality
5. Run the test suite: `pytest`
6. Run linters: `ruff check . && black . && mypy src/seismic_linter`
7. Commit with descriptive message
8. Push and create a Pull Request

### Development Setup

```bash
git clone https://github.com/AmanSinghNp/seismic-linter.git
cd seismic-linter
python -m venv venv
# On Windows: .\venv\Scripts\activate
# On macOS/Linux: source venv/bin/activate
source venv/bin/activate
pip install -e .[dev]
pre-commit install
```
> **Note**: The pre-commit hook uses `language: system`, so `seismic-linter` must be available on your PATH (e.g. installed in your active virtual environment).

Cache is keyed by absolute path and is not portable across machines or directories.

### Coding Standards
- Follow PEP 8 (enforced by Black and Ruff)
- Write docstrings for all public functions
- Add type hints
- Maintain test coverage above 90%

### Testing Guidelines
- Unit tests in `tests/`
- Name test files `test_*.py`
- Use descriptive test names
- Include both positive and negative cases

### Pull Request Process
- PRs should be <400 lines when possible (excluding auto-generated files or large test datasets)
- Link related issues
- Update documentation if needed
- Wait for CI to pass
- Respond to review comments

### Code Review
All submissions require review. We aim to provide feedback within 48 hours.

### Configuration
In `[tool.seismic-linter]`, `fail_on` replaces the default list of rules that cause a non-zero exit (it does not merge with defaults).

## Questions?
Open a discussion on GitHub or submit an issue.
