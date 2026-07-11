import hashlib
import random
from datetime import datetime, timedelta, timezone

from tools import mock_apis

_GENERATION_BASE_TIMESTAMP = datetime(2026, 7, 11, 12, 0, tzinfo=timezone.utc)

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
        "beneficiary_name": "Global Trading Partners LLC",
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
        "beneficiary_name": "Silk Road Holdings Ltd",
    },
}

# Lets a curated scenario also be looked up by its own transaction_id
# (e.g. "txn_001"), not just its friendly name ("clean_coffee").
_SCENARIOS_BY_TRANSACTION_ID = {scenario["transaction_id"]: scenario for scenario in SCENARIOS.values()}

_GENERATED_ACCOUNT_IDS = [f"acct_{4001 + i}" for i in range(15)]
_GENERATED_DEVICE_IDS = [f"dev_{101 + i}" for i in range(15)]
_GENERATED_MERCHANT_IDS = [
    "merch_amazon",
    "merch_starbucks",
    "merch_uber",
    "merch_whole_foods",
    "merch_delta_airlines",
    "merch_best_buy",
    "merch_crypto_exchange_1",
    "merch_western_union",
    "merch_online_casino_1",
    "merch_luxury_watches",
    "merch_gift_card_kiosk",
    "merch_used_car_dealer",
]
_GENERATED_IP_KEYS = [
    "ip_us_chicago",
    "ip_us_austin",
    "ip_us_miami",
    "ip_us_seattle",
    "ip_uk_london",
    "ip_ca_toronto",
    "ip_de_berlin",
    "ip_fr_paris",
    "ip_au_sydney",
    "ip_ru_moscow",
    "ip_cn_shanghai",
    "ip_br_saopaulo",
    "ip_in_mumbai",
    "ip_ae_dubai",
    "ip_ng_abuja",
]
# Well-known, stable public resolvers so freshly-generated transactions still
# exercise the identity_verifier agent's live MCP geolocation tool call.
_REAL_IP_POOL = ["8.8.8.8", "8.8.4.4", "1.1.1.1", "9.9.9.9", "208.67.222.222", "105.112.0.1"]
_TRANSACTION_TYPES = ["card_present", "card_not_present", "wire_transfer"]
_CLEAN_BENEFICIARY_NAMES = ["New Horizon Ventures Inc", "Harborview Trading Co", "Blue Ridge Logistics LLC"]
_RISKY_BENEFICIARY_NAMES = ["Quicksilver Capital Group", "Meridian Offshore Holdings", "Silk Road Holdings Ltd"]

RISKY_GENERATION_PROBABILITY = 0.15


def _generate_transaction(transaction_id: str) -> dict:
    seed = int(hashlib.sha256(transaction_id.encode()).hexdigest(), 16)
    rng = random.Random(seed)

    account_id = rng.choice(_GENERATED_ACCOUNT_IDS)
    low, high = mock_apis.ACCOUNT_HISTORY[account_id]["typical_range"]
    is_risky = rng.random() < RISKY_GENERATION_PROBABILITY

    known_devices = [d for d in _GENERATED_DEVICE_IDS if mock_apis.DEVICE_FINGERPRINTS[d]["known"]]
    unknown_devices = [d for d in _GENERATED_DEVICE_IDS if not mock_apis.DEVICE_FINGERPRINTS[d]["known"]]
    high_risk_merchants = [m for m in _GENERATED_MERCHANT_IDS if mock_apis.MERCHANT_RISK[m]["tier"] == "high"]
    low_risk_merchants = [m for m in _GENERATED_MERCHANT_IDS if mock_apis.MERCHANT_RISK[m]["tier"] != "high"]

    if is_risky:
        amount = round(rng.uniform(high * 2, high * 6), 2)
        device_id = rng.choice(unknown_devices)
        merchant_id = rng.choice(high_risk_merchants)
    else:
        amount = round(rng.uniform(low, high), 2)
        device_id = rng.choice(known_devices)
        merchant_id = rng.choice(low_risk_merchants)

    txn_type = rng.choice(_TRANSACTION_TYPES)
    transaction = {
        "transaction_id": transaction_id,
        "account_id": account_id,
        "amount": amount,
        "merchant_id": merchant_id,
        "device_id": device_id,
        "ip": rng.choice(_GENERATED_IP_KEYS),
        "real_ip": rng.choice(_REAL_IP_POOL),
        "timestamp": (_GENERATION_BASE_TIMESTAMP + timedelta(minutes=rng.randint(-500000, 500000))).isoformat(),
        "type": txn_type,
        "source": "generated",
    }

    if txn_type == "wire_transfer":
        transaction["beneficiary_is_new"] = is_risky
        transaction["beneficiary_name"] = rng.choice(
            _RISKY_BENEFICIARY_NAMES if is_risky else _CLEAN_BENEFICIARY_NAMES
        )

    return transaction


def get_scenario(identifier: str) -> dict:
    if not identifier:
        raise KeyError("Transaction ID cannot be empty")

    if identifier in SCENARIOS:
        return {**SCENARIOS[identifier], "source": "curated"}
    if identifier in _SCENARIOS_BY_TRANSACTION_ID:
        return {**_SCENARIOS_BY_TRANSACTION_ID[identifier], "source": "curated"}

    return _generate_transaction(identifier)
