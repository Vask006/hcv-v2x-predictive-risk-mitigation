# Claims ↔ phase ↔ modules (living matrix)

**Source specification:** [../patent/utility-model-specification.md](../patent/utility-model-specification.md)

Update this table when implementation advances.

| Claim (summary) | Target phase | Key modules / artifacts (this repo) | Notes |
|-----------------|---------------|----------------------------------------|--------|
| **1** Integrated OBU + V2X + cloud; predict & mitigate in real time | Ph. 0–1 (partial) → 3–5 | `edge/*`, `cloud/api`, contracts | V2X and full cloud ML are phased; see PHASED_IMPLEMENTATION.md. |
| **2** OBU sensor fusion & edge risk (vehicle, environment, driver) | Ph. 1 (partial) → 2 | `risk_engine/scorer.py`, `inference/perception_adapter.py`, recordings | Perception/driver/CAN largely mock or absent until Phase 2+. |
| **3** V2X: V2V, V2I, V2N cooperative safety | Ph. 3 | TBD (e.g. `risk_engine/context_provider` or new `v2x/` module) | Not in current tree. |
| **4** Cloud ML on historical + real-time fleet data | Ph. 4 | `cloud/*` extension, ML pipeline TBD | Ingest exists; ML training/inference not in repo yet. |
| **5** Alerts, fleet notifications, cooperative mitigation | Ph. 1 (partial) → 3–5 | `event_store/`, `uploader/`, `contracts/event_v1.json` | Mitigation as **payload** + upload; HMI/V2X broadcast Phase 3+. |
| **6** Fleet-configurable policies & compliance | Ph. 5 | `cloud/dashboard/`, config service TBD | Device YAML today; fleet multi-tenant TBD. |

**Legend:** “partial” = demonstrator supports the narrative without covering every embodiment in the specification.
