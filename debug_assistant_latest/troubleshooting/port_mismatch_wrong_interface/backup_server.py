#!/usr/bin/env python3
from http.server import BaseHTTPRequestHandler, HTTPServer
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            message = "Hello from port_mismatch_wrong_interface test!"
            self.wfile.write(bytes(message, "utf8"))
        except Exception as e:
            logger.error(f"Error handling request: {e}")
            try:
                self.send_error(500, f"Internal server error: {e}")
            except:
                pass  # Headers already sent, can't send error response

if __name__ == '__main__':
    # BUG 1: Binding to localhost instead of 0.0.0.0
    server_address = ('localhost', 8765)  # Should be ('0.0.0.0', 8765)
    httpd = HTTPServer(server_address, SimpleHTTPRequestHandler)
    logger.info(f'Server running on {server_address[0]}:{server_address[1]}')
    httpd.serve_forever()
