from __future__ import annotations

from typing import Any

import requests
import streamlit as st


def _safe_get(d: dict[str, Any], *keys: str) -> Any:
    cur: Any = d
    for key in keys:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(key)
    return cur


def _extract_row(item: dict[str, Any]) -> dict[str, Any]:
    payload = item.get("payload", {}) if isinstance(item, dict) else {}
    risk = _safe_get(payload, "risk") or {}
    psummary = _safe_get(payload, "perception_summary") or {}
    mitigation = psummary.get("mitigation", {}) if isinstance(psummary, dict) else {}
    return {
        "event_id": item.get("event_id"),
        "device_id": item.get("device_id"),
        "recorded_at": item.get("recorded_at"),
        "riskScore": risk.get("score"),
        "severity": risk.get("band"),
        "hazardType": psummary.get("hazard_type"),
        "reasonCodes": risk.get("reason_codes"),
        "driverAlert": mitigation.get("driverAlert"),
        "fleetNotification": mitigation.get("fleetNotification"),
        "latitude": _safe_get(payload, "gps", "latitude_deg"),
        "longitude": _safe_get(payload, "gps", "longitude_deg"),
    }


st.set_page_config(page_title="HCV V2X Predictive Risk Dashboard", layout="wide")
st.title("HCV V2X Predictive Risk Dashboard")

api_base = st.sidebar.text_input("API Base URL", value="http://127.0.0.1:8000")
refresh = st.sidebar.button("Refresh")

if refresh:
    st.rerun()

health_ok = False
items: list[dict[str, Any]] = []
error_message = None

try:
    health = requests.get(f"{api_base.rstrip('/')}/health", timeout=3)
    health_ok = health.ok
except requests.RequestException as exc:
    error_message = f"Cloud API unavailable: {exc}"

if health_ok:
    st.success("Cloud API connection: healthy")
    try:
        resp = requests.get(f"{api_base.rstrip('/')}/v1/events?limit=50", timeout=5)
        if resp.ok:
            body = resp.json()
            if isinstance(body, dict):
                raw_items = body.get("items", [])
                if isinstance(raw_items, list):
                    items = [i for i in raw_items if isinstance(i, dict)]
        else:
            error_message = f"Failed to load events: HTTP {resp.status_code}"
    except requests.RequestException as exc:
        error_message = f"Failed to load events: {exc}"
else:
    st.warning("Cloud API connection: unavailable")
    if error_message:
        st.info(error_message)

rows = [_extract_row(i) for i in items]
latest = rows[0] if rows else {}

col1, col2, col3 = st.columns(3)
col1.metric("Total Events", len(rows))
col2.metric("Latest Risk Score", latest.get("riskScore") if rows else "N/A")
col3.metric("Latest Severity", latest.get("severity") if rows else "N/A")

col4, col5, col6 = st.columns(3)
col4.metric("Latest Hazard Type", latest.get("hazardType") if rows else "N/A")
col5.metric("Latest Driver Alert", latest.get("driverAlert") if rows else "N/A")
col6.metric("Latest Fleet Notification", latest.get("fleetNotification") if rows else "N/A")

st.subheader("Recent Events")
if rows:
    st.dataframe(rows, use_container_width=True)
else:
    st.info("No events available yet. Run the demo script and refresh.")
