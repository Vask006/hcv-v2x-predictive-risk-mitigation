# Contributing

Thank you for your interest in contributing to HCV V2X Predictive Risk Mitigation.

## Project Scope

This project focuses on deterministic, testable, local-demo-ready edge/cloud safety workflows for heavy commercial vehicles.

## Local Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
```

## Run Tests

```bash
bash scripts/run_all_tests.sh
```

## Branch Naming

Suggested branch naming:

- `feature/<short-description>`
- `fix/<short-description>`
- `docs/<short-description>`
- `chore/<short-description>`

## Coding Standards

- Keep service boundaries clear.
- Add tests for new behavior.
- Prefer deterministic logic over implicit behavior.
- Use typed Python where reasonable.
- Avoid hardcoded secrets or environment-specific paths.
- Update docs when behavior changes.

## Pull Request Expectations

- Provide a concise summary and motivation.
- Reference related issues when available.
- Include test evidence (commands and results).
- Keep scope focused and reviewable.

## Commit Message Examples

- `Add V2X context merge support to pipeline`
- `Improve telemetry normalization for mixed key styles`
- `Add dashboard resilience for missing API fields`

## Adding a New Service

1. Create `services/<service-name>/src`.
2. Add tests under `services/<service-name>/tests`.
3. Document service purpose, inputs, outputs, and run/test commands.
4. Wire service into pipeline only through explicit interfaces.

## Adding Tests

- Add tests near the service being changed.
- Keep tests deterministic and hardware-optional.
- Avoid real network calls unless explicitly integration-scoped.

## Updating Docs

- Update relevant service README files.
- Update root `README.md` for command/workflow changes.
- Keep architecture and demo docs consistent with behavior.

## Issue Reporting

When filing issues, include:

- expected behavior
- actual behavior
- reproduction steps
- environment details
- relevant logs or output snippets
