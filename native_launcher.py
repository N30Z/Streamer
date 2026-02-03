import threading
import webview
import sys
from src.aniworld.__main__ import main

def start_backend():
    sys.argv = ["aniworld", "--web-ui -wN"]
    main()

if __name__ == "__main__":
    t = threading.Thread(target=start_backend, daemon=True)
    t.start()

    webview.create_window(
        title="Streamer",
        url="http://127.0.0.1:5000",  # adjust if your app uses another port
        width=1200,
        height=800,
    )
    webview.start()