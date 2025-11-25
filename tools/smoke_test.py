import requests, json, io, sys

BASE = 'http://127.0.0.1:5000'

s = requests.Session()

print('GET /api/site-content ->', s.get(BASE + '/api/site-content').status_code)
sc = s.get(BASE + '/api/site-content').json()
print('site_content keys:', list(sc.keys()))

# Login
r = s.post(BASE + '/api/admin-login', json={'username':'admin','password':'joni8252'})
print('login:', r.status_code, r.text)
if r.status_code != 200:
    print('Login failed, aborting'); sys.exit(1)

# Save a test "why" block
payload = {'updates': {'why': {'title': 'SMOKE Why Title', 'description': 'SMOKE Why Description', 'amenity1': 'Smoke A1', 'amenity2': 'Smoke A2', 'amenity3': 'Smoke A3'}}}
resp = s.post(BASE + '/api/admin/update-site-content', json=payload)
print('/api/admin/update-site-content ->', resp.status_code, resp.text)

# Upload a tiny PNG
png_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\nIDATx\x9cc`\x00\x00\x00\x02\x00\x01\xe2!\xbc3\x00\x00\x00\x00IEND\xaeB`\x82"
files = {'file': ('smoke.png', io.BytesIO(png_bytes), 'image/png')}
up = s.post(BASE + '/api/admin/upload-about-image', files=files)
print('/api/admin/upload-about-image ->', up.status_code, up.text)

upload_url = None
try:
    upload_url = up.json().get('url')
except Exception:
    pass

# Verify site-content about.photos contains it
sc_after = s.get(BASE + '/api/site-content').json()
print('about.photos after upload ->', sc_after.get('about', {}).get('photos', []))

# Cleanup uploaded image if any
if upload_url:
    rem = s.post(BASE + '/api/admin/remove-about-image', json={'image_url': upload_url})
    print('/api/admin/remove-about-image ->', rem.status_code, rem.text)
    sc_final = s.get(BASE + '/api/site-content').json()
    print('about.photos final ->', sc_final.get('about', {}).get('photos', []))

print('Done')
