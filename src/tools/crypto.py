import httpx


async def get_bitcoin_price(currency: str = "usd") -> dict:
    """Get the current Bitcoin price from CoinGecko.

    Args:
        currency: Target currency code (e.g. "usd", "eur", "gbp")
    """
    currency = currency.lower()

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://api.coingecko.com/api/v3/simple/price",
            params={
                "ids": "bitcoin",
                "vs_currencies": currency,
                "include_24hr_change": "true",
            },
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()

    btc = data["bitcoin"]
    return {
        "currency": currency.upper(),
        "price": btc[currency],
        "change_24h_pct": btc.get(f"{currency}_24h_change"),
    }
