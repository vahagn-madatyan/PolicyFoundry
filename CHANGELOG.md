# Changelog

All notable changes to this project will be documented in this file.

## [0.2.0] - 2026-03-17

### Added

- **PyPI publishing** -- package is now installable via `pip install policy-foundry`
- **GitHub Actions CI/CD** -- automated publishing to PyPI and TestPyPI on tag push
- **Change request template** -- professional Excel template with metadata header, data validation dropdowns, and styled formatting (`examples/templates/change_request_template.xlsx`)
- **SECURITY.md** -- vulnerability reporting policy via LinkedIn DM
- **CONTRIBUTING.md** -- contributor setup guide, code style, and PR guidelines
- **CHANGELOG.md** -- this file

### Fixed

- **Bedrock provider support** -- switched from hardcoded `instructor.Mode.JSON` to provider-aware mode selection; Bedrock now uses `TOOLS` mode via LiteLLM for reliable structured output
- **Structured output reliability** -- replaced bare `list[dict]` fields in `TrafficAnalysis` and `SecurityAssessment` with typed Pydantic sub-models (`TopTalker`, `PortDistributionEntry`, `Anomaly`, `BandwidthOutlier`, `RiskScore`, `RuleGap`), giving the LLM clear schema guidance
- **Error diagnostics** -- `LLM_PARSE_FAILED` errors now log the actual validation error instead of the raw user message
- **API key leak to Bedrock** -- `api_key` and `api_base` are no longer passed to LiteLLM when not set, preventing Bedrock from receiving irrelevant OpenAI keys
- **Template fill for complex templates** -- `_fill_template()` now scans rows 1-20 for the header row instead of only row 1, supporting templates with metadata sections above the data table

### Changed

- **Package name** -- renamed from `policyfoundry` to `policy-foundry` on PyPI
- **License** -- corrected from BSL-1.1 to Apache-2.0 in `pyproject.toml`
- **Project metadata** -- added author, classifiers, and project URLs
- **README** -- rewritten with end-user installation section (pip/pipx/uv) and contributor build-from-source section
- **Examples directory** -- renamed `referance/samples/` to `examples/input/`, removed development artifacts (images, generated outputs), renamed sample file to `sample-traffic.xlsx`

## [0.1.0] - 2026-03-15

### Added

- Initial release
- Excel traffic export analysis pipeline
- VPC Flow Log analysis (local and S3)
- 5-stage LangGraph AI pipeline (Analyze, Assess, Generate, Validate, Decide)
- Rich terminal and JSON output formatters
- Change request export (xlsx and pdf)
- AWS Security Group adapter with constraint validation
- Ollama, OpenAI, and Bedrock LLM provider support
- YAML + environment variable configuration system
- Docker Compose setup with Ollama sidecar
