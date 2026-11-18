import json
import urllib.request
import subprocess
import os

# 1. Acquire real JWT token
payload = json.dumps({"email": "admin@truthlens.local", "password": "AdminPass123!"}).encode()
req = urllib.request.Request("http://127.0.0.1:8000/api/auth/login", data=payload, headers={"Content-Type": "application/json"})
res = json.loads(urllib.request.urlopen(req).read().decode())
token = res["access_token"]
print("[1] Token acquired:", token[:30], "...")

# 2. Check that /api/auth/me accepts this token
me_req = urllib.request.Request("http://127.0.0.1:8000/api/auth/me", headers={"Authorization": f"Bearer {token}"})
me_res = json.loads(urllib.request.urlopen(me_req).read().decode())
print("[2] /api/auth/me returned user:", me_res["email"], "role:", me_res["role"])

# 3. Check /api/dashboard/summary
dash_req = urllib.request.Request("http://127.0.0.1:8000/api/dashboard/summary", headers={"Authorization": f"Bearer {token}"})
dash_res = json.loads(urllib.request.urlopen(dash_req).read().decode())
print("[3] /api/dashboard/summary returned verifications:", dash_res["total_verifications"], "mismatches:", dash_res["integrity_mismatches"])

print("[*] All APIs tested and fully functional!")

