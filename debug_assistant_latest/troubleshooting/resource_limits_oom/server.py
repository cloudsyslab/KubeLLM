#!/usr/bin/env python3
from http.server import BaseHTTPRequestHandler, HTTPServer
import sys
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Allocate memory to simulate a real application
# This will cause OOM when memory limit is too low
logger.info("Starting server and allocating memory...")
# Allocate approximately 70MB of memory
large_list = [0] * (10 * 1024 * 1024)  # 10M integers ~ 80MB
logger.info(f"Memory allocated. List size: {sys.getsizeof(large_list) / (1024*1024):.2f} MB")

class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            message = "Hello from resource_limits_oom test! Server is running."
            self.wfile.write(bytes(message, "utf8"))
        except Exception as e:
            logger.error(f"Error handling request: {e}")
            try:
                self.send_error(500, f"Internal server error: {e}")
            except:
                pass  # Headers already sent, can't send error response

if __name__ == '__main__':
    server_address = ('0.0.0.0', 8080)
    httpd = HTTPServer(server_address, SimpleHTTPRequestHandler)
    logger.info(f'Server running on {server_address[0]}:{server_address[1]}')
    httpd.serve_forever()
