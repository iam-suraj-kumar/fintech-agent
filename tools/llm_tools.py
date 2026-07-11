from langchain_core.tools import tool

from tools.mock_apis import (
    check_sanctions_list as _check_sanctions_list,
    get_account_history as _get_account_history,
    get_device_fingerprint as _get_device_fingerprint,
    get_geolocation as _get_geolocation,
    get_merchant_risk_score as _get_merchant_risk_score,
    search_similar_fraud_cases as _search_similar_fraud_cases,
)


@tool
def account_history(account_id: str) -> dict:
    """Look up an account's typical spending pattern: amount range, home country, and average transactions per week."""
    return _get_account_history(account_id)


@tool
def device_fingerprint(device_id: str) -> dict:
    """Look up whether a device ID is known for the account and how long ago it was first seen."""
    return _get_device_fingerprint(device_id)


@tool
def geolocation(ip: str) -> dict:
    """Look up the country and city associated with an IP address."""
    return _get_geolocation(ip)


@tool
def merchant_risk_score(merchant_id: str) -> dict:
    """Look up a merchant's risk tier (low/medium/high) and numeric risk score."""
    return _get_merchant_risk_score(merchant_id)


@tool
def similar_fraud_cases(description: str) -> list[str]:
    """Search a database of past confirmed fraud cases for ones textually similar to the given transaction description."""
    return _search_similar_fraud_cases(description)


@tool
def sanctions_check(beneficiary_name: str) -> dict:
    """Check whether a wire transfer beneficiary name appears on a sanctions watchlist."""
    return _check_sanctions_list(beneficiary_name)
