"""Risk scoring utilities for Phase 1 runtime.

The dict-based scorer in ``risk_engine.scorer`` is the default for ``edge_runtime``.
Optional integration with ``services/risk-engine`` uses ``risk_engine.service_adapter``
when ``risk_engine.use_service_adapter`` or ``HCV_USE_SERVICE_RISK_ENGINE`` is enabled;
see ``docs/runtime-unification-plan.md`` and ``docs/refactor-status.md``.
"""
