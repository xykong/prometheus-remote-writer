# AGENTS.md - Coding Guidelines for prometheus-remote-writer

This guide is for agentic coding assistants working on the `prometheus-remote-writer` Python library.

## Project Overview

Python library for writing time-series data using the Prometheus Remote Write protocol. Supports Python 3.9+.
Uses uv for dependency management, pytest for testing, and flake8 for linting.

## Build/Test/Lint Commands

### Setup
```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv pip install -e ".[dev]"

# OR use the local venv
source .venv/bin/activate
uv pip install -e ".[dev]"
```

### Running Tests
```bash
# Run all tests
make test
# OR
pytest

# Run specific test file
pytest tests/test_remote_writer_mocks.py

# Run single test function
pytest tests/test_remote_writer_mocks.py::TestRemoteWriter::test_initialization_defaults

# Run with verbose output
pytest -v

# Run with coverage
pytest --cov=prometheus_remote_writer
```

### Linting
```bash
# Run flake8 (critical errors only)
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics

# Run full flake8 (with warnings)
flake8 . --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics

# OR use Makefile
make lint
```

### Building
```bash
# Build package
python -m build

# Run all checks (clean, lint, test, tox)
make check
```

### Other Commands
```bash
# Generate protobuf files
make proto

# Clean build artifacts
make clean
```

## Code Style Guidelines

### Import Organization
```python
# 1. Standard library imports (grouped by category)
import logging
from dataclasses import dataclass
from typing import (
    Dict,
    List,
    Optional,
    Sequence,
    Tuple,
)

# 2. Third-party imports
import requests
import snappy
from requests import Response, Session

# 3. Local imports (with # noqa if needed for generated code)
from prometheus_remote_writer.proto.remote_pb2 import WriteRequest  # noqa
```

- Use absolute imports, not relative
- Group imports logically
- Multi-line imports: use parentheses with one item per line

### Type Annotations

**MANDATORY**: All functions and methods MUST have type annotations.

```python
# ✓ CORRECT
def send(self, metrics: Sequence[MetricItem]) -> SendResult:
    """Send metrics to Prometheus."""
    pass

def _normalize_timestamps(
    self,
    timestamps: Sequence[Union[int, float]],
    metric_index: int,
) -> List[int]:
    """Normalize timestamps to milliseconds."""
    pass

# ✗ WRONG - Missing type hints
def send(self, metrics):
    pass
```

- Use `typing` module types: `Optional`, `Union`, `Sequence`, `Mapping`, `Dict`, `List`
- Prefer `Sequence` over `List` for input parameters (more flexible)
- Prefer `Mapping` over `Dict` for input parameters (more flexible)
- Use `List` for return types and internal variables
- Use `TypedDict` for structured dictionaries with known keys
- Use `@dataclass` for data containers with behavior

### Formatting

- **Line length**: Max 127 characters (flake8 configured)
- **Indentation**: 4 spaces (standard Python)
- **String quotes**: Single quotes `'string'` preferred (based on codebase pattern)
- **Docstrings**: Use triple double-quotes `"""docstring"""`

### Naming Conventions

```python
# Classes: PascalCase
class RemoteWriter:
    pass

class SendResult:
    pass

# Constants: UPPER_SNAKE_CASE
DEFAULT_HEADERS = {...}
MS_THRESHOLD = 10_000_000_000

# Functions/methods: snake_case
def send(self, metrics):
    pass

def _normalize_timestamps(self):  # Private: prefix with _
    pass

# Variables: snake_case
total_samples = 0
is_seconds = True
```

### Error Handling

```python
# Raise RuntimeError for network/HTTP errors with context
try:
    resp = self._session.post(url, ...)
    resp.raise_for_status()
except requests.HTTPError as e:
    raise RuntimeError(
        f"HTTP error posting to {self.url}: status={status}, body={body_snippet}"
    ) from e
except requests.RequestException as e:
    raise RuntimeError(
        f"Network error posting to {self.url}: {e.__class__.__name__}: {e}"
    ) from e

# Raise ValueError for invalid input with details
if len(values) != len(timestamps):
    raise ValueError(
        f"Metric item at index {idx} has length mismatch: "
        f"values={len(values)} vs timestamps={len(timestamps)}"
    )
```

- Use `raise ... from e` to preserve exception chain
- Provide detailed context in error messages
- Include variable values and indices in validation errors

### Testing Patterns

```python
# Use pytest, unittest.mock for mocking
from unittest.mock import patch, MagicMock
import pytest

# Test class pattern
class TestRemoteWriter:
    def test_initialization_defaults(self):
        writer = RemoteWriter(url="http://example.com")
        assert writer.url == "http://example.com"
        
    @patch.object(requests.Session, "post")
    def test_send_message_success(self, mock_post):
        mock_resp = MagicMock(spec=Response)
        mock_resp.status_code = 200
        mock_post.return_value = mock_resp
        # Test logic...

# Skip unimplemented tests
@pytest.mark.skip(reason="This test is not yet implemented")
def test_future_feature():
    pass
```

## Architecture Guidelines

### File Structure
```
prometheus_remote_writer/
├── __init__.py          # Main RemoteWriter class + types
├── proto/               # Generated protobuf files (DO NOT EDIT)
│   ├── remote_pb2.py
│   └── types_pb2.py
tests/
├── test_remote_writer.py           # Basic tests
├── test_remote_writer_mocks.py     # Unit tests with mocks
├── test_remote_writer_local.py     # Local integration tests
└── test_remote_writer_integration.py  # External integration tests
```

### Code Organization Principles

1. **Public API first**: Public methods at top of class, internal helpers below
2. **Type safety**: Use dataclasses and TypedDict for structured data
3. **Separation of concerns**: Convert → Batch → Build → Send (clear pipeline)
4. **Resource management**: Support context managers (`__enter__`/`__exit__`)

### Key Patterns

```python
# Use dataclass for simple data containers
@dataclass
class SendResult:
    requests_sent: int
    series_sent: int

# Use TypedDict for API contracts
class MetricItem(TypedDict):
    metric: Dict[str, str]
    values: List[Union[int, float]]

# Context manager support
def __enter__(self):
    return self

def __exit__(self, exc_type, exc, tb):
    self.close()
```

## DO NOT

- ❌ Edit generated protobuf files in `prometheus_remote_writer/proto/`
- ❌ Suppress type errors or use `# type: ignore` without strong reason
- ❌ Commit without running tests and linter
- ❌ Use `print()` for debugging (use `logging` module)
- ❌ Exceed 127 character line length
- ❌ Add dependencies without updating `pyproject.toml`

## Version Control

- Main branch: `master`
- Use git-flow: `git flow release start/finish`
- CI runs on: Python 3.9, 3.10, 3.11
- License: Apache 2.0
