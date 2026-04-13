"""
Local image server utility for the formatting MCP server.
Provides a background HTTP server to serve local images to Playwright/Gemini.
"""

import http.server
import threading
import logging
from pathlib import Path
from typing import List, Optional

# Get a logger for this module
logger = logging.getLogger(__name__)

# Module-level state for the background server
_server_started: bool = False
_server_port: int = 8000

def start_image_server(port: int = 8000) -> Optional[int]:
    """
    Starts a local HTTP server in a background thread to serve images
    from the 'test_images' directory.
    
    Args:
        port: The port number to use for the local server.
        
    Returns:
        Optional[int]: The port number if successful, or None if the directory is missing.
    """
    global _server_started, _server_port
    
    if _server_started:
        return _server_port

    # Use the local 'test_images' directory relative to this file
    images_dir = Path(__file__).parent / "test_images"
    if not images_dir.exists():
        logger.error(f"Image server failed to start: Directory not found at {images_dir}")
        return None

    class QuietImageHandler(http.server.SimpleHTTPRequestHandler):
        """Custom handler that serves from a specific directory and suppresses logs."""
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(images_dir), **kwargs)
        
        def log_message(self, format, *args):
            """Override to prevent flooding the logs with every image request."""
            pass

    try:
        server = http.server.HTTPServer(("", port), QuietImageHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        
        _server_started = True
        _server_port = port
        logger.info(f"Image server started at http://localhost:{port} serving {images_dir}")
        return port
        
    except OSError as e:
        # Port might be in use, assume it's already running or another process has it
        logger.info(f"Image server already active or port {port} unavailable: {e}")
        _server_started = True
        _server_port = port
        return port

def prepare_image_urls(images: List[List[str]], port: int = 8000) -> List[List[str]]:
    """
    Converts local image filenames to localhost URLs for AI consumption.
    
    Input format: [[filename, caption], ...]
    Output format: [[url, caption], ...]
    
    Args:
        images: A list of image entries [filename/url, caption].
        port: The port where the image server is running.
        
    Returns:
        List[List[str]]: Processed list with updated image sources.
    """
    processed_images = []
    
    for img_entry in images:
        if not isinstance(img_entry, list) or len(img_entry) < 1:
            processed_images.append(img_entry)
            continue
            
        src = img_entry[0]
        caption = img_entry[1] if len(img_entry) > 1 else ""
        
        # If it's already a URL or base64 data, leave it as is
        if src.startswith(("http", "data:", "https")):
            processed_images.append(img_entry)
        else:
            # Convert local filename to a localhost URL
            url = f"http://localhost:{port}/{src}"
            processed_images.append([url, caption])
            
    return processed_images
