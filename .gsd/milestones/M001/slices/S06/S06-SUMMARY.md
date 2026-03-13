---
id: S06
parent: M001
milestone: M001
provides:
  - "LLMClient class with async complete() for structured Pydantic output"
  - "create_llm_client factory with Ollama health check"
  - "Dual retry: Instructor validation (3x) + tenacity transient (3x)"
  - "Provider-agnostic model name composition (ollama_chat, openai, bedrock, anthropic)"
requires: []
affects: []
key_files:
  - src/policyfoundry/pipeline/llm.py
key_decisions:
  - "Used instructor.from_litellm(acompletion, mode=JSON) for async structured output"
  - "ollama_chat/ prefix for Ollama (chat endpoint produces better structured JSON)"
  - "Pyright type: ignore for litellm dynamic exception types and instructor dynamic client"
  - "Health check only for Ollama provider (skip for cloud providers)"
patterns_established:
  - "Instructor + LiteLLM wrapper for structured LLM output"
  - "Dual retry layers: inner validation retries, outer transient retries"
  - "Provider health checking at client creation time"
observability_surfaces: []
drill_down_paths: []
duration: 5min
verification_result: passed
completed_at: 2026-03-11
blocker_discovered: false
---
# S06: LLM Integration

## What Was Delivered

Async LLMClient wrapping Instructor + LiteLLM for structured Pydantic output with dual retry layers (3x validation, 3x transient with exponential backoff), Ollama health checking at creation, and provider-agnostic model name routing. 7/7 must-haves verified.

## Key Outcomes

- **T01**: LLMClient with `complete(messages, response_model)` → validated Pydantic object. create_llm_client factory with Ollama health check (unreachable + model-not-found detection). Provider routing for ollama_chat, openai, bedrock, anthropic.

## Verification

All 7 verification truths passed: LiteLLM routing, Pydantic parsing, validation retry, transient retry, provider switching, unreachable detection, model-not-found detection.

---
*Completed: 2026-03-11*
