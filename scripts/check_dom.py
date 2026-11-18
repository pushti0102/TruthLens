import subprocess

chrome_path = r'C:\Program Files\Google\Chrome\Application\chrome.exe'
cmd = [chrome_path, '--headless=new', '--user-data-dir=C:\\Users\\HPV\\AppData\\Local\\Temp\\chrome_test', '--dump-dom', 'http://127.0.0.1:5173/login']
res = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
idx = res.stdout.find('id="root"')
if idx != -1:
    print('FOUND ROOT:')
    print(res.stdout[idx:idx+2500])
else:
    print('id="root" not found')

