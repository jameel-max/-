import requests

response = requests.post('http://127.0.0.1:5000/reserve', json={
    'name': 'جميل',
    'time': '11:00 صباحاً'
})

print(response.json())