"""Risk scoring utilities for Phase 1 runtime.

The dict-based scorer in ``risk_engine.scorer`` powers ``edge_runtime`` and is not
interchangeable with ``services/risk-engine`` (typed ``RiskEngine`` / different
payload). See repo ``docs/refactor-status.md`` before consolidating implementations.
"""
