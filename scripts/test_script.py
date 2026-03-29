import requests

# Get token
resp = requests.post("http://localhost:8000/auth/login", data={"username": "alice_admin", "password": "password"})
token = resp.json().get("access_token")

# Get sessions
resp2 = requests.get("http://localhost:8000/sessions/", headers={"Authorization": f"Bearer {token}"})
print(resp2.status_code)
print(resp2.text)
