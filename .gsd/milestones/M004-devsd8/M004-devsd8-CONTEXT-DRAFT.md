---
depends_on: [M003-2heki1]
---

# M004-devsd8: Secrets Management — DRAFT

**Status:** Draft — needs dedicated discussion before planning

This is seed material from the M003/M004 discussion. A future session should conduct a focused discussion to finalize scope, resolve open questions, and produce a full CONTEXT.md.

## What Was Discussed

### Core Intent
Add secure secrets management to PolicyFoundry so users don't need to put API keys in YAML config files or manually export env vars. Two mechanisms:

1. **`.env` file support** — pydantic-settings native `DotEnvSettingsSource`, loaded from project directory
2. **OS credential store** — `keyring` library for macOS Keychain and Windows Credential Manager

### Confirmed Decisions
- **Config merge priority (confirmed):** init → env vars → `.env` → keychain → local YAML → global YAML
- **CLI surface (confirmed):** `policyfoundry secret set/get/delete` as its own subcommand group (not under `config`)
- **Platform scope (confirmed):** macOS Keychain + Windows Credential Manager only. Linux falls back to `.env` / env vars.
- **`keyring` is optional dependency** — tool works without it, graceful fallback

### Key Technical Signals
- pydantic-settings has native `env_file` support via `SettingsConfigDict(env_file='.env')` — no new dependency
- `keyring` library (jaraco/keyring) is the Python standard for credential storage — used by `gh`, `twine`, etc.
- Custom `PydanticBaseSettingsSource` subclass needed for keyring integration into the priority chain
- Existing `settings_customise_sources` in `config/models.py` is the extension point
- `keyring` API is minimal: `get_password(service, username)` / `set_password(service, username, password)` / `delete_password(service, username)`
- Service name convention: `"policyfoundry"`, username convention: `"llm.api_key"` (dotted config path)

### Provisional Requirements
- R501 — .env file loading integrated into config priority chain
- R502 — OS credential store integration (macOS Keychain, Windows Credential Manager)
- R503 — Secret management CLI commands (set/get/delete)
- R504 — Graceful fallback when keyring package not installed

### Open Questions for Future Discussion
- Should `policyfoundry secret set` accept arbitrary key names or only known config paths?
- Should there be a `policyfoundry secret list` command showing what's stored (names only, not values)?
- Should `.env` file path be configurable or always `.env` in CWD?
- How should the Docker container handle keyring (no OS keychain available)?
- Should `policyfoundry init` generate a `.env.example` file alongside the YAML template?
