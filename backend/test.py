import json
import time
from datetime import datetime
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def quarter_code(dt: datetime) -> int:
    q = (dt.month - 1) // 3 + 1
    return dt.year * 100 + q + 12


def fetch_json(url: str, timeout: float = 20.0, retries: int = 3, backoff: float = 0.8):
    last_err = None
    headers = {"Accept": "application/json", "User-Agent": "python-urllib"}
    for i in range(max(1, retries)):
        try:
            req = Request(url, headers=headers, method="GET")
            with urlopen(req, timeout=timeout) as resp:
                raw = resp.read()
            return json.loads(raw.decode("utf-8", errors="strict"))
        except Exception as e:
            last_err = e
            time.sleep(backoff * (2**i))
    raise RuntimeError(str(last_err))


purchase_price = 350000
province = "GELDERLAND"
start_dt = datetime(2014, 12, 15)
end_dt = datetime.now()
startquarter = quarter_code(start_dt)
endquarter = quarter_code(end_dt)

base = "https://vastgoeddashboard.kadaster.nl/woningwaardecalculatorproxy/api/v1/propertyvalue/calculate"
params = {
    "province": province.upper(),
    "startquarter": int(startquarter),
    "endquarter": int(endquarter),
    "startprice": int(purchase_price),
}
url = base + "?" + urlencode(params)

data = fetch_json(url)
print(data)
rows_used = 1

if isinstance(data, dict):
    price_new = data.get("priceNew") or data.get("estimatedValue")
    price_change = data.get("priceChange")
    message = data.get("message")
    if not price_new:
        result = json.dumps({"url": url, "response": data}, ensure_ascii=False)
    else:
        parts = [
            f"Aankoopprijs: €{purchase_price:,}".replace(",", "."),
            f"Geschatte huidige waarde: {price_new}",
        ]
        if price_change:
            parts.append(f"Waardestijging (provinciale prijsindex): {price_change}")
        parts.append(
            f"Provincie: {province.upper()} | startquarter={startquarter} | endquarter={endquarter}"
        )
        if message:
            parts.append(f"Opmerking: {message}")
        result = "\n".join(parts)
else:
    result = json.dumps({"url": url, "response": data}, ensure_ascii=False)
print(result)
