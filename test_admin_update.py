import requests
import time

LOGIN_URL = 'http://127.0.0.1:5000/api/admin-login'
UPDATE_URL = 'http://127.0.0.1:5000/api/admin/update-site-content'
GET_URL = 'http://127.0.0.1:5000/api/site-content'

s = requests.Session()
resp = s.post(LOGIN_URL, json={"username":"admin","password":"joni8252"}, timeout=5)
print('login', resp.status_code, resp.text)

new_title = f"TEST HERO {int(time.time())}"
resp2 = s.post(UPDATE_URL, json={"updates": {"hero": {"title": new_title}}}, timeout=5)
print('update', resp2.status_code, resp2.text)

resp3 = requests.get(GET_URL, timeout=5)
print('site-content hero title:', resp3.status_code, resp3.json().get('hero', {}).get('title'))
