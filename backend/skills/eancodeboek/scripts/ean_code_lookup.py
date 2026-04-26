import requests


def get_ecb_infoset(product, limit=100, offset=0, **kwargs):
    """
    Search for metering points (EAN codes) via the EDSN API.

    Args:
        product (str): 'ELK' or 'GAS'.
        limit (int): Results per page (max 1000).
        offset (int): Starting position.
        **kwargs: Search parameters (postalCode, streetNumber, city, etc.)
    """
    base_url = "https://gateway.edsn.nl/eancodeboek/v1/ecbinfoset"

    # 1. Basic validation
    if product not in ["ELK", "GAS"]:
        raise ValueError("Product must be 'ELK' or 'GAS'")

    # 2. Define allowed parameter combinations (excluding product, limit, offset)
    allowed_combos = [
        {"postalCode"},
        {"postalCode", "streetNumber"},
        {"postalCode", "streetNumber", "streetNumberAddition"},
        {"city", "specialMeteringPoint"},
        {"city", "street", "streetNumber"},
        {"city", "street", "streetNumber", "streetNumberAddition"},
    ]

    # 3. Check if current kwargs match any allowed combination
    current_keys = set(kwargs.keys())
    if current_keys not in allowed_combos:
        valid_options = ", ".join([str(c) for c in allowed_combos])
        raise ValueError(f"Invalid parameter combination. Allowed: {valid_options}")

    # 4. Construct parameters for the request
    params = {
        "product": product,
        "limit": min(limit, 1000),  # Cap at 1000 per documentation
        "offset": offset,
        **kwargs,
    }

    try:
        # Note: You likely need an API Key/Auth header for the real gateway.edsn.nl
        headers = {"Accept": "application/json"}
        response = requests.get(base_url, params=params, headers=headers)
        response.raise_for_status()
        return response.json()

    except requests.exceptions.RequestException as e:
        return {"error": str(e)}
