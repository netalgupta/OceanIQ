"""
Unit tests for Proactive Anomaly Agent & Hobday (2016) MHW Climatology Math.
"""

import pytest
from src.agents.anomaly_agent import _classify_mhw_severity, scan_for_anomalies


def test_mhw_severity_classification():
    assert _classify_mhw_severity(3.8) == "CRITICAL"
    assert _classify_mhw_severity(2.8) == "SEVERE"
    assert _classify_mhw_severity(1.8) == "STRONG"
    assert _classify_mhw_severity(1.0) == "MODERATE"
    assert _classify_mhw_severity(0.5) == "ADVISORY"


@pytest.mark.asyncio
async def test_scan_for_anomalies_execution():
    alerts = await scan_for_anomalies()
    assert len(alerts) >= 1
    for alert in alerts:
        assert "alert_type" in alert
        assert alert["alert_type"] in ("MARINE_HEATWAVE", "HYPOXIA")
        assert "severity" in alert
        assert "policy_advisory" in alert
        assert "affected_species" in alert
        assert len(alert["affected_species"]) >= 1
