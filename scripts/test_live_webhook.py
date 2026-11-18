import requests

res = requests.get("https://rully-rully4.vercel.app/api/telegram-webhook/info")
print("Status code:", res.status_code)
print("Response JSON:", res.json())
