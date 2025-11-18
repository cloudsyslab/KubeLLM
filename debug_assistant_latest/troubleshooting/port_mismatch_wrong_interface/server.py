#!/usr/bin/env python3
from http.server import BaseHTTPRequestHandler, HTTPServer

class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        message = "Hello from port_mismatch_wrong_interface test!"
        self.wfile.write(bytes(message, "utf8"))

if __name__ == '__main__':
    # BUG 1: Binding to localhost instead of 0.0.0.0
    server_address = ('localhost', 8765)  # Should be ('0.0.0.0', 8765)
    httpd = HTTPServer(server_address, SimpleHTTPRequestHandler)
    print(f'Server running on {server_address[0]}:{server_address[1]}')
    httpd.serve_forever()
