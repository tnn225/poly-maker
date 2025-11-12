import requests
import json

def get_bid_ask(market_token: str):
    """
    Fetch the order book for a given market token from Polymarket API.
    
    Returns a dictionary with 'bids' and 'asks' lists.
    Each list contains dictionaries with 'price' and 'size'.
    """
    url = f"https://gamma-api.polymarket.com/markets/{market_token}/orderbook?level=2"
    response = requests.get(url)
    
    if response.status_code != 200:
        raise Exception(f"Error fetching order book: {response.status_code} {response.text}")
    
    data = response.json()
    return {
        "bid": data.get("bids", []),
        "ask": data.get("asks", [])
    }

def get_markets(slug: str):
    """
    Fetch Polymarket market by slug and return a dictionary mapping outcomes to token IDs.
    
    Example:
        slug = "btc-updown-15m-1762600500"
        returns: {"Up": "2086...", "Down": "1800..."}
    """
    url = f"https://gamma-api.polymarket.com/markets/slug/{slug}"
    response = requests.get(url)
    
    if response.status_code != 200:
        raise Exception(f"Error fetching market: {response.status_code} {response.text}")
    
    data = response.json()
    
    # Parse stringified JSON arrays
    outcomes = json.loads(data.get("outcomes", "[]"))
    token_ids = json.loads(data.get("clobTokenIds", "[]"))
    
    # Map outcomes to token IDs
    market_tokens = dict(zip(outcomes, token_ids))
    
    return market_tokens

# === Example usage ===
if __name__ == "__main__":
    slug = "btc-updown-15m-1762600500"
    tokens = get_markets(slug)
    print(f"Market Tokens for {slug}:")
    for outcome, token_id in tokens.items():
        print(f"  {outcome}: {token_id}")
