# T01: 06-llm-integration 01

**Slice:** S06 — **Milestone:** M001

## Description

Build the LLM client layer that all pipeline stages will call. Creates an async LLMClient class that wraps Instructor + LiteLLM for structured Pydantic output with automatic validation retries and transient network retries. Includes provider health checking and model name composition.

Purpose: Phase 7 pipeline stages need a `client.complete(messages, response_model)` method that returns validated Pydantic objects. This plan delivers that interface with full error handling.
Output: `pipeline/llm.py` module with LLMClient class and create_llm_client factory, plus comprehensive unit tests.

## Must-Haves

- [ ] "LLM calls go through LiteLLM and reach Ollama when configured as the provider"
- [ ] "LLM responses are parsed into Pydantic models without free-text parsing"
- [ ] "When structured output parsing fails, the system retries with validation error fed back to LLM"
- [ ] "When transient errors occur (connection, timeout), the system retries with exponential backoff"
- [ ] "Switching LLM provider in config works without code changes"
- [ ] "Unreachable Ollama is detected at client creation with actionable error"
- [ ] "Missing Ollama model is detected at client creation with available models listed"

## Files

- `pyproject.toml`
- `uv.lock`
- `src/policyfoundry/pipeline/llm.py`
- `src/policyfoundry/pipeline/__init__.py`
- `tests/test_pipeline/__init__.py`
- `tests/test_pipeline/conftest.py`
- `tests/test_pipeline/test_llm.py`
