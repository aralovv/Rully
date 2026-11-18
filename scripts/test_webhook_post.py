import requests

update_payload = {
    "update_id": 99999999,
    "message": {
        "message_id": 1,
        "date": 1700000000,
        "chat": {
            "id": 999999999,
            "type": "private"
        },
        "from": {
            "id": 999999999,
            "is_bot": False,
            "first_name": "TestBot",
            "username": "testuser"
        },
        "text": "/help"
    }
}

res = requests.post("https://rully-rully4.vercel.app/api/telegram-webhook", json=update_payload)
print("Status code:", res.status_code)
print("Response text:", res.text)
