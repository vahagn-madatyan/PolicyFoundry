# S06: Llm Integration

**Goal:** Build the LLM client layer that all pipeline stages will call.
**Demo:** Build the LLM client layer that all pipeline stages will call.

## Must-Haves


## Tasks

- [x] **T01: 06-llm-integration 01** `est:5min`
  - Build the LLM client layer that all pipeline stages will call. Creates an async LLMClient class that wraps Instructor + LiteLLM for structured Pydantic output with automatic validation retries and transient network retries. Includes provider health checking and model name composition.

Purpose: Phase 7 pipeline stages need a `client.complete(messages, response_model)` method that returns validated Pydantic objects. This plan delivers that interface with full error handling.
Output: `pipeline/llm.py` module with LLMClient class and create_llm_client factory, plus comprehensive unit tests.

## Files Likely Touched

- `pyproject.toml`
- `uv.lock`
- `src/policyfoundry/pipeline/llm.py`
- `src/policyfoundry/pipeline/__init__.py`
- `tests/test_pipeline/__init__.py`
- `tests/test_pipeline/conftest.py`
- `tests/test_pipeline/test_llm.py`
