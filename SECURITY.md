# Security Policy

## Reporting a Vulnerability

Please do not open public GitHub issues for suspected security vulnerabilities.

Report vulnerabilities privately to the repository maintainers through GitHub private reporting (if enabled) or direct maintainer contact.

Include:

- vulnerability description
- potential impact
- reproduction steps
- affected files/components
- suggested remediation if available

## Secrets and Credentials

- Do not commit secrets, credentials, private keys, or tokens.
- Use `.env` locally and keep only `.env.example` in source control.

## Supported Versions

- `main` branch is the actively supported version for security fixes.

## Local Demo Disclaimer

This repository is designed for local/demo workflows and development validation.
It is not a production-hardened deployment out of the box.
