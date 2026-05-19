import requests
from config import Config

params = {
    "q": "machine learning",
    "api_key": Config.SERPAPI_KEY,
    "engine": "google",
    "num": 3
}
try:
    response = requests.get("https://serpapi.com/search", params=params, timeout=10)
    data = response.json()
    print("Status:", response.status_code)
    if "error" in data:
        print("Error:", data["error"])
    else:
        print("Organic results:", len(data.get("organic_results", [])))
except Exception as e:
    print("Exception:", e)