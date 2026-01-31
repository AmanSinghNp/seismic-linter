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
6. Run linters: `ruff check . && black . && mypy seismic_linter/`
7. Commit with descriptive message
8. Push and create a Pull Request

### Development Setup

```bash
git clone https://github.com/yourusername/seismic-linter.git
cd seismic-linter
python -m venv venv
source venv/bin/activate
pip install -e .[dev]
pre-commit install
```

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

## Questions?
Open a discussion on GitHub or reach out via [contact method].
