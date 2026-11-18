import urllib.request
import json
import subprocess
import os

# 1. Login via backend API to get real token
login_data = json.dumps({"email": "admin@truthlens.local", "password": "AdminPass123!"}).encode()
req = urllib.request.Request("http://127.0.0.1:8000/api/auth/login", data=login_data, headers={"Content-Type": "application/json"})
resp = urllib.request.urlopen(req)
token_res = json.loads(resp.read().decode())
token = token_res["access_token"]
print("Acquired token for admin:", token[:30], "...")

# 2. Create an HTML runner that sets localStorage and redirects to /dashboard
setup_html = f"""
<!DOCTYPE html>
<html>
<body>
<script>
localStorage.setItem('tl_token', '{token}');
localStorage.setItem('tl_user', JSON.stringify({json.dumps(token_res)}));
window.location.href = 'http://127.0.0.1:5173/dashboard';
</script>
</body>
</html>
"""
setup_path = os.path.abspath("scripts/inject_token.html")
with open(setup_path, "w") as f:
    f.write(setup_html)

# 3. Launch Chrome on inject_token.html, wait 3 seconds, dump DOM of /dashboard
chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
cmd = [
    chrome_path,
    "--headless=new",
    "--user-data-dir=C:\\Users\\HPV\\AppData\\Local\\Temp\\chrome_dash_test",
    f"file:///{setup_path.replace(os.sep, '/')}",
]
# First visit inject_token to populate localStorage
subprocess.run(cmd + ["--virtual-time-budget=2000"], timeout=10)

# Now visit /dashboard directly in that profile and screenshot
dash_cmd = [
    chrome_path,
    "--headless=new",
    "--user-data-dir=C:\\Users\\HPV\\AppData\\Local\\Temp\\chrome_dash_test",
    "--screenshot=d:\\TruthLens-main\\dashboard_screenshot.png",
    "--window-size=1280,900",
    "http://127.0.0.1:5173/dashboard",
]
subprocess.run(dash_cmd + ["--virtual-time-budget=4000"], timeout=15)

# Check DOM
dom_res = subprocess.run([
    chrome_path,
    "--headless=new",
    "--user-data-dir=C:\\Users\\HPV\\AppData\\Local\\Temp\\chrome_dash_test",
    "--dump-dom",
    "http://127.0.0.1:5173/dashboard"
], capture_output=True, text=True, timeout=15)

idx = dom_res.stdout.find("Welcome back")
if idx != -1:
    print("SUCCESS: Dashboard rendered! Found:", dom_res.stdout[idx:idx+200])
else:
    idx_root = dom_res.stdout.find('id="root"')
    print("Dashboard DOM slice:", dom_res.stdout[idx_root:idx_root+500])

