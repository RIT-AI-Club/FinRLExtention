import http.server
import threading
import socket
from pathlib import Path
from typing import List, Tuple
import logging

logger = logging.getLogger(__name__)

def get_free_port():
    """Returns a free port on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        return s.getsockname()[1]

_server_started = False
_server_port = 8000

def start_image_server(port: int = 8000):
    """
    Starts a local HTTP server in a background thread to serve images
    from the test_images directory.
    """
    global _server_started, _server_port
    if _server_started:
        return _server_port

    charts_dir = Path(__file__).parent / "test_images"
    if not charts_dir.exists():
        logger.error(f"Warning: {charts_dir} does not exist.")
        return None

    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(charts_dir), **kwargs)
        
        def log_message(self, format, *args):
            # Quiet server
            pass

    try:
        server = http.server.HTTPServer(("", port), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        _server_started = True
        _server_port = port
        logger.info(f"Image server started at http://localhost:{port} serving {charts_dir}")
        return port
    except OSError:
        # Likely already running
        _server_started = True
        _server_port = port
        return port

def prepare_image_urls(images: List[List[str]], port: int = 8000) -> List[List[str]]:
    """
    Converts image filenames to local localhost URLs.
    Input format: [[filename, caption], ...]
    """
    processed_images = []
    for img_entry in images:
        if isinstance(img_entry, list) and len(img_entry) >= 1:
            src = img_entry[0]
            caption = img_entry[1] if len(img_entry) > 1 else ""
            
            # If it's already a URL or base64, keep it
            if src.startswith(("http", "data:", "https")):
                processed_images.append(img_entry)
            else:
                # Convert filename to local URL
                url = f"http://localhost:{port}/{src}"
                processed_images.append([url, caption])
        else:
            processed_images.append(img_entry)
    return processed_images
