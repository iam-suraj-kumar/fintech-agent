from datetime import datetime, timezone

# `ip`/`prior_ip` are symbolic lookup keys into tools.mock_apis.GEOLOCATIONS,
# used by the deterministic triage node so triage stays fast and offline.
# `real_ip` is a genuine public IP address, used only by the identity_verifier
# specialist agent's live MCP geolocation tool call.
SCENARIOS = {
    "clean_coffee": {
        "transaction_id": "txn_001",
        "account_id": "acct_3003",
        "amount": 6.50,
        "merchant_id": "merch_coffee_1",
        "device_id": "dev_known_1",
        "ip": "ip_us_ny",
        "real_ip": "8.8.8.8",
        "timestamp": datetime(2026, 7, 11, 9, 0, tzinfo=timezone.utc).isoformat(),
        "type": "card_present",
    },
    "impossible_travel": {
        "transaction_id": "txn_002",
        "account_id": "acct_1001",
        "amount": 340.00,
        "merchant_id": "merch_electronics_1",
        "device_id": "dev_new_1",
        "ip": "ip_ng_lagos",
        "real_ip": "105.112.0.1",
        "timestamp": datetime(2026, 7, 11, 14, 10, tzinfo=timezone.utc).isoformat(),
        "type": "card_not_present",
        "prior_ip": "ip_us_ny",
        "prior_timestamp": datetime(2026, 7, 11, 14, 0, tzinfo=timezone.utc).isoformat(),
    },
    "borderline_wire": {
        "transaction_id": "txn_003",
        "account_id": "acct_2002",
        "amount": 18000.00,
        "merchant_id": "merch_wire_intl_1",
        "device_id": "dev_known_1",
        "ip": "ip_us_sf",
        "real_ip": "1.1.1.1",
        "timestamp": datetime(2026, 7, 11, 16, 30, tzinfo=timezone.utc).isoformat(),
        "type": "wire_transfer",
        "beneficiary_is_new": True,
    },
    "borderline_restart_demo": {
        "transaction_id": "txn_004",
        "account_id": "acct_2002",
        "amount": 9500.00,
        "merchant_id": "merch_wire_intl_1",
        "device_id": "dev_new_1",
        "ip": "ip_us_sf",
        "real_ip": "8.8.4.4",
        "timestamp": datetime(2026, 7, 11, 17, 0, tzinfo=timezone.utc).isoformat(),
        "type": "wire_transfer",
        "beneficiary_is_new": True,
    },
}


def get_scenario(name: str) -> dict:
    if name not in SCENARIOS:
        raise KeyError(f"Unknown scenario: {name}")
    return dict(SCENARIOS[name])
