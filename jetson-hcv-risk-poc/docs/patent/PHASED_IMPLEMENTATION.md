# Phase-wise implementation (aligned with utility model)

This plan ties **repository work** to the **specification** in [utility-model-specification.md](./utility-model-specification.md). Status is indicative—update as features land.

| Phase | Goal (engineering) | Specification alignment (sections / claims) | Status |
|-------|-------------------|-----------------------------------------------|--------|
| **Phase 0** | Baseline sensing, contracts, cloud skeleton: geo-tagged events schema, smoke tests, disk recording (camera + optional GPS), connectivity logging. | OBU sensing subset (camera, GNSS position) · foundation for §6.1 · contract boundary for cloud. | **Implemented** — see repo README “Phase 0”. |
| **Phase 1** | Edge runtime: sample recordings, heuristic risk scoring, mock perception/context, durable event queue, HTTPS upload to cloud API. | §6.1 edge processing & risk indicators (partial) · §6.3 ingest path (without full ML platform) · §6.4 mitigation metadata in events (not full HMI/V2X actuation). Claims **1–2** (partial), **5** (partial, alerts as data). | **Implemented** — `PHASE1_POC_ARCHITECTURE.md`, `edge/app/edge_runtime.py`. |
| **Phase 2** | Harden OBU: real perception path (e.g. TensorRT), richer fusion, **segmented video** / clean finalize for field reliability, optional CAN/OBD read if available. | §6.1 full OBU narrative (progressive). Claim **2** strengthening. | **Planned** |
| **Phase 3** | **V2X path:** ingest cooperative data (simulated or real radio stack / broker), map to context provider, emit cooperative-oriented fields in events or side channels. | §6.2 · §6.4 cooperative messages. Claim **3** · **5** (mitigation messaging). | **Planned** |
| **Phase 4** | **Cloud analytics:** training/inference pipeline for fleet risk, batch + streaming, dashboard integration beyond basic query. | §6.3 ML on historical + real-time data. Claim **4**. | **Planned** |
| **Phase 5** | **Fleet & compliance:** multi-tenant policy config, audit reports, insurance-oriented exports; optional driver HMI integration. | §6.5 · §6.4 driver warnings at vehicle. Claims **5–6**. | **Planned** |

## Principles

1. **Each phase** should leave a **demo-able, testable** increment (scenarios under `docs/scenarios/` when added).
2. **Mock vs real** components must stay explicit in architecture docs (as in Phase 1).
3. **Claim mapping** is maintained in [../patent-mapping/claim-phase-matrix.md](../patent-mapping/claim-phase-matrix.md).

## Dependencies between phases

- Phase **2** builds on Phase **0–1** recordings and risk pipeline.
- Phase **3** benefits from stable Phase **2** OBU outputs.
- Phase **4** needs ingest volume and labels from fleet pilots (often parallel to Phase **3**).
- Phase **5** typically follows operational confidence in **4** and policy requirements.

## Out of scope for this repository (unless added later)

- Certified V2X radio stacks, homologation, production CAN safety cases.
- Legal interpretation of claim scope (counsel).
