import uvicorn
import asyncio
import threading
import sys
import traceback
import time
from urllib.request import urlopen

sys.path.append("d:\\QuMail\\backend")

from main import app

def hang_detector():
    time.sleep(5) # wait for startup
    print("Checking if /health is responsive...")
    try:
        response = urlopen("http://127.0.0.1:8000/health", timeout=3)
        print("Responsive:", response.read())
    except Exception as e:
        print("It hangs:", e)
        print("Dumping thread stacks:")
        for th in threading.enumerate():
            print(th)
            traceback.print_stack(sys._current_frames()[th.ident])
            print("---")
        sys.exit(1)

if __name__ == "__main__":
    t = threading.Thread(target=hang_detector, daemon=True)
    t.start()
    uvicorn.run(app, host="127.0.0.1", port=8000)
