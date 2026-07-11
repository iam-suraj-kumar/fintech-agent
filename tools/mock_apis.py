# These three of each are the exact fixtures the four curated demo scenarios
# in data/synthetic_transactions.py were tuned against - don't change them.
ACCOUNT_HISTORY = {
    "acct_1001": {"typical_range": (5, 150), "country": "US", "avg_txn_count_per_week": 12},
    "acct_2002": {"typical_range": (500, 5000), "country": "US", "avg_txn_count_per_week": 3},
    "acct_3003": {"typical_range": (10, 80), "country": "US", "avg_txn_count_per_week": 20},
}

DEVICE_FINGERPRINTS = {
    "dev_known_1": {"known": True, "first_seen_days_ago": 412},
    "dev_new_1": {"known": False, "first_seen_days_ago": 0},
}

GEOLOCATIONS = {
    "ip_us_ny": {"country": "US", "city": "New York"},
    "ip_ng_lagos": {"country": "NG", "city": "Lagos"},
    "ip_us_sf": {"country": "US", "city": "San Francisco"},
}

MERCHANT_RISK = {
    "merch_coffee_1": {"tier": "low", "score": 0.05},
    "merch_wire_intl_1": {"tier": "high", "score": 0.72},
    "merch_electronics_1": {"tier": "medium", "score": 0.35},
}

# A larger pool on top of the curated fixtures above, so tool lookups for
# freshly-generated transactions (see data/synthetic_transactions.py) don't
# always hit the same handful of records.
ACCOUNT_HISTORY.update(
    {
        "acct_4001": {"typical_range": (20, 300), "country": "US", "avg_txn_count_per_week": 8},
        "acct_4002": {"typical_range": (50, 1200), "country": "US", "avg_txn_count_per_week": 15},
        "acct_4003": {"typical_range": (5, 60), "country": "GB", "avg_txn_count_per_week": 25},
        "acct_4004": {"typical_range": (200, 8000), "country": "US", "avg_txn_count_per_week": 4},
        "acct_4005": {"typical_range": (10, 120), "country": "CA", "avg_txn_count_per_week": 10},
        "acct_4006": {"typical_range": (30, 400), "country": "US", "avg_txn_count_per_week": 18},
        "acct_4007": {"typical_range": (1000, 15000), "country": "US", "avg_txn_count_per_week": 2},
        "acct_4008": {"typical_range": (15, 90), "country": "DE", "avg_txn_count_per_week": 12},
        "acct_4009": {"typical_range": (40, 500), "country": "US", "avg_txn_count_per_week": 9},
        "acct_4010": {"typical_range": (5, 45), "country": "US", "avg_txn_count_per_week": 30},
        "acct_4011": {"typical_range": (100, 2500), "country": "FR", "avg_txn_count_per_week": 5},
        "acct_4012": {"typical_range": (25, 350), "country": "US", "avg_txn_count_per_week": 14},
        "acct_4013": {"typical_range": (500, 20000), "country": "US", "avg_txn_count_per_week": 1},
        "acct_4014": {"typical_range": (8, 75), "country": "AU", "avg_txn_count_per_week": 22},
        "acct_4015": {"typical_range": (60, 900), "country": "US", "avg_txn_count_per_week": 7},
    }
)

DEVICE_FINGERPRINTS.update(
    {
        "dev_101": {"known": True, "first_seen_days_ago": 620},
        "dev_102": {"known": True, "first_seen_days_ago": 45},
        "dev_103": {"known": False, "first_seen_days_ago": 0},
        "dev_104": {"known": True, "first_seen_days_ago": 210},
        "dev_105": {"known": False, "first_seen_days_ago": 0},
        "dev_106": {"known": True, "first_seen_days_ago": 900},
        "dev_107": {"known": True, "first_seen_days_ago": 15},
        "dev_108": {"known": False, "first_seen_days_ago": 0},
        "dev_109": {"known": True, "first_seen_days_ago": 380},
        "dev_110": {"known": True, "first_seen_days_ago": 5},
        "dev_111": {"known": False, "first_seen_days_ago": 0},
        "dev_112": {"known": True, "first_seen_days_ago": 730},
        "dev_113": {"known": True, "first_seen_days_ago": 90},
        "dev_114": {"known": False, "first_seen_days_ago": 0},
        "dev_115": {"known": True, "first_seen_days_ago": 260},
    }
)

GEOLOCATIONS.update(
    {
        "ip_us_chicago": {"country": "US", "city": "Chicago"},
        "ip_us_austin": {"country": "US", "city": "Austin"},
        "ip_us_miami": {"country": "US", "city": "Miami"},
        "ip_us_seattle": {"country": "US", "city": "Seattle"},
        "ip_uk_london": {"country": "GB", "city": "London"},
        "ip_ca_toronto": {"country": "CA", "city": "Toronto"},
        "ip_de_berlin": {"country": "DE", "city": "Berlin"},
        "ip_fr_paris": {"country": "FR", "city": "Paris"},
        "ip_au_sydney": {"country": "AU", "city": "Sydney"},
        "ip_ru_moscow": {"country": "RU", "city": "Moscow"},
        "ip_cn_shanghai": {"country": "CN", "city": "Shanghai"},
        "ip_br_saopaulo": {"country": "BR", "city": "Sao Paulo"},
        "ip_in_mumbai": {"country": "IN", "city": "Mumbai"},
        "ip_ae_dubai": {"country": "AE", "city": "Dubai"},
        "ip_ng_abuja": {"country": "NG", "city": "Abuja"},
    }
)

MERCHANT_RISK.update(
    {
        "merch_amazon": {"tier": "low", "score": 0.03},
        "merch_starbucks": {"tier": "low", "score": 0.04},
        "merch_uber": {"tier": "low", "score": 0.08},
        "merch_whole_foods": {"tier": "low", "score": 0.02},
        "merch_delta_airlines": {"tier": "medium", "score": 0.25},
        "merch_best_buy": {"tier": "medium", "score": 0.20},
        "merch_crypto_exchange_1": {"tier": "high", "score": 0.65},
        "merch_western_union": {"tier": "high", "score": 0.58},
        "merch_online_casino_1": {"tier": "high", "score": 0.80},
        "merch_luxury_watches": {"tier": "medium", "score": 0.40},
        "merch_gift_card_kiosk": {"tier": "high", "score": 0.62},
        "merch_used_car_dealer": {"tier": "medium", "score": 0.30},
    }
)

SANCTIONS_LIST = {
    "silk road holdings ltd": {
        "list_name": "OFAC SDN (mock)",
        "reason": "shell entity linked to a prior enforcement action",
    },
}

FRAUD_CASE_TEXTS = [
    "Card-not-present purchase for $2,340 at an electronics merchant the "
    "cardholder never used before, from a new device, immediately followed "
    "by a request to ship to a freight-forwarding address.",
    "International wire transfer of $18,000 to a newly added beneficiary "
    "within 10 minutes of the beneficiary being added to the account.",
    "Series of small $1-3 test transactions at unrelated online merchants "
    "within a 2-minute window, typical of card validation/testing fraud.",
    "Account login from a new device and new country followed within "
    "minutes by a large balance transfer.",
]

_store = None


def get_account_history(account_id: str) -> dict:
    return ACCOUNT_HISTORY.get(
        account_id,
        {"typical_range": (0, 100), "country": "US", "avg_txn_count_per_week": 5},
    )


def get_device_fingerprint(device_id: str) -> dict:
    return DEVICE_FINGERPRINTS.get(device_id, {"known": False, "first_seen_days_ago": 0})


def get_geolocation(ip: str) -> dict:
    return GEOLOCATIONS.get(ip, {"country": "US", "city": "Unknown"})


def get_merchant_risk_score(merchant_id: str) -> dict:
    return MERCHANT_RISK.get(merchant_id, {"tier": "medium", "score": 0.3})


def check_sanctions_list(beneficiary_name: str) -> dict:
    entry = SANCTIONS_LIST.get(beneficiary_name.strip().lower())
    if entry:
        return {"on_list": True, **entry}
    return {"on_list": False, "list_name": None, "reason": None}


def _get_store():
    global _store
    if _store is None:
        from langchain_chroma import Chroma
        from langchain_openai import OpenAIEmbeddings

        _store = Chroma.from_texts(FRAUD_CASE_TEXTS, OpenAIEmbeddings())
    return _store


def search_similar_fraud_cases(query: str, k: int = 2) -> list[str]:
    store = _get_store()
    docs = store.similarity_search(query, k=k)
    return [doc.page_content for doc in docs]
