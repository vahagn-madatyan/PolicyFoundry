# Security Policy

## Supported Versions

| Version | Supported |
| --- | --- |
| 0.1.x | Yes |

## Reporting a Vulnerability

**Please do not open a public GitHub issue for security vulnerabilities.**

Instead, report vulnerabilities privately by sending a direct message on LinkedIn:

[linkedin.com/in/mvahagn](https://www.linkedin.com/in/mvahagn)

Please include:

- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

You should receive an acknowledgment within 48 hours. We will work with you to understand the issue and coordinate a fix before any public disclosure.

## Scope

Security issues in the following areas are in scope:

- Command injection via CLI inputs
- Insecure handling of API keys or credentials
- LLM prompt injection that bypasses safety controls
- Unintended modification of live firewall rules
- Dependency vulnerabilities with known exploits

## Security Design

PolicyFoundry is designed with the following security principles:

- **Read-only by default** -- all firewall adapters are wrapped in a read-only safety layer and never modify live rules
- **No credential storage** -- API keys are read from environment variables or config files, never stored by the application
- **Structured LLM output** -- all LLM responses are validated through Pydantic models, reducing prompt injection risk
