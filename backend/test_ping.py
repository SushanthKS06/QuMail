import asyncio
# ... wait we can just run via python code to ping the API ...
import urllib.request
import time

print("Pinging backend...")
try:
    start = time.time()
    req = urllib.request.urlopen("http://127.0.0.1:8000/api/v1/auth/status", timeout=3)
    print("Response:", req.read())
    print("Time:", time.time() - start)
except Exception as e:
    print("Error:", e)
