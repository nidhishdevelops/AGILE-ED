import requests

topic = "feature engineering"
url = "https://www.googleapis.com/books/v1/volumes"
params = {
    "q": f"{topic} data science",
    "maxResults": 3,
    "printType": "books"
}
response = requests.get(url, params=params)
print("Status:", response.status_code)
data = response.json()
print("Total items:", data.get('totalItems', 0))
if data.get('items'):
    for item in data['items']:
        print(" -", item['volumeInfo'].get('title'))
else:
    print("No books found.")