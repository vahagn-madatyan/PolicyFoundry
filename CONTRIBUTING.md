# Contributing to Policy Foundry

Thanks for your interest in contributing! This guide will help you get started.

## Getting Started

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- [Ollama](https://ollama.com/) (for running tests that hit an LLM)

### Setup

```bash
git clone https://github.com/vahagn-madatyan/PolicyFoundry.git
cd PolicyFoundry
uv sync --group dev
```

### Verify your setup

```bash
uv run pytest
uv run policyfoundry --help
```

## Making Changes

1. **Fork the repo** and create a branch from `main`
2. **Make your changes** -- keep commits focused and atomic
3. **Add tests** for new functionality
4. **Run the test suite** before submitting:
   ```bash
   uv run pytest
   ```
5. **Open a pull request** against `main`

## Project Structure

```text
src/policyfoundry/
├── adapters/      # Firewall vendor adapters
├── analysis/      # Traffic analysis & aggregation
├── config/        # Configuration management
├── ingestion/     # Data ingestion (local, S3, Excel)
├── pipeline/      # AI analysis pipeline (LangGraph)
├── storage/       # Parquet persistence + DuckDB queries
├── output/        # Terminal & JSON formatters
└── export/        # Change request export (xlsx/pdf)
```

## Code Style

- Use type hints on all function signatures
- Follow existing patterns in the codebase
- Async functions for all I/O operations (adapters, pipeline stages, storage)
- Pydantic models for data structures

## Testing

- Tests live in `tests/` mirroring the `src/` structure
- Use `pytest` with `pytest-asyncio` (auto mode)
- AWS services are mocked with [moto](https://github.com/getmoto/moto)
- Run a specific test: `uv run pytest tests/test_export/ -v`

## Pull Requests

- Keep PRs focused on a single change
- Write a clear description of what and why
- Link any related issues
- All tests must pass before merge

## Reporting Bugs

Open an issue on [GitHub Issues](https://github.com/vahagn-madatyan/PolicyFoundry/issues) with:

- Steps to reproduce
- Expected vs actual behavior
- PolicyFoundry version (`policyfoundry --version`)
- Python version and OS

## Security Issues

See [SECURITY.md](SECURITY.md) for reporting vulnerabilities. Do not open public issues for security bugs.

## License

By contributing, you agree that your contributions will be licensed under the [Apache License 2.0](LICENSE).
