import urllib.request
import json

# 1. Login
data_json = json.dumps({'email': 'user@truthlens.local', 'password': 'UserPass123!'}).encode()
req = urllib.request.Request('http://127.0.0.1:8000/api/auth/login', data=data_json, headers={'Content-Type': 'application/json'})
token = json.loads(urllib.request.urlopen(req).read().decode())['access_token']

# 2. Build multipart form data for upload
boundary = '----WebKitFormBoundary7MA4YWxkTrZu0gW'
with open('truthlens-ai/data/real/sample_photo.jpg', 'rb') as f:
    img_bytes = f.read()

parts = [
    f'--{boundary}\r\n'.encode(),
    b'Content-Disposition: form-data; name="file"; filename="sample_photo.jpg"\r\n',
    b'Content-Type: image/jpeg\r\n\r\n',
    img_bytes,
    f'\r\n--{boundary}--\r\n'.encode(),
]
body = b''.join(parts)

req2 = urllib.request.Request(
    'http://127.0.0.1:8000/api/media/verify',
    data=body,
    headers={
        'Content-Type': f'multipart/form-data; boundary={boundary}',
        'Authorization': f'Bearer {token}'
    }
)
res = json.loads(urllib.request.urlopen(req2).read().decode())
print('FULL VERIFICATION PIPELINE RESULT:')
print(json.dumps(res, indent=2))

