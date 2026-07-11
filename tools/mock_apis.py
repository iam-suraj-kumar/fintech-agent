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
