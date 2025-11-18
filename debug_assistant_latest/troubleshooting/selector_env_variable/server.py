#!/usr/bin/env python3
from http.server import BaseHTTPRequestHandler, HTTPServer
import os

# BUG: Application requires APP_MESSAGE env var but it's not defined in deployment
APP_MESSAGE = os.environ['APP_MESSAGE']  # Will raise KeyError if not set

class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        message = f"{APP_MESSAGE} (from env var)"
        self.wfile.write(bytes(message, "utf8"))

if __name__ == '__main__':
    server_address = ('0.0.0.0', 8080)
    httpd = HTTPServer(server_address, SimpleHTTPRequestHandler)
    print(f'Server running on {server_address[0]}:{server_address[1]}')
    print(f'APP_MESSAGE: {APP_MESSAGE}')
    httpd.serve_forever()
