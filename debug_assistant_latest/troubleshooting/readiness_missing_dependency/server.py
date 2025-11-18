#!/usr/bin/env python3
from http.server import BaseHTTPRequestHandler, HTTPServer
import requests  # BUG: This package is not installed in Dockerfile

class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            # Try to use requests library to demonstrate it's installed
            message = f"Hello! Requests library version: {requests.__version__}"
            self.wfile.write(bytes(message, "utf8"))
        except Exception as e:
            print(f"Error handling request: {e}")
            self.send_error(500, f"Internal server error: {e}")

if __name__ == '__main__':
    server_address = ('0.0.0.0', 8080)
    httpd = HTTPServer(server_address, SimpleHTTPRequestHandler)
    print(f'Server running on {server_address[0]}:{server_address[1]}')
    httpd.serve_forever()
