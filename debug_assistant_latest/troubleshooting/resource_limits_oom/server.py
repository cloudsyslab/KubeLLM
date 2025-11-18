#!/usr/bin/env python3
from http.server import BaseHTTPRequestHandler, HTTPServer
import sys

# Allocate memory to simulate a real application
# This will cause OOM when memory limit is too low
print("Starting server and allocating memory...")
# Allocate approximately 70MB of memory
large_list = [0] * (10 * 1024 * 1024)  # 10M integers ~ 80MB
print(f"Memory allocated. List size: {sys.getsizeof(large_list) / (1024*1024):.2f} MB")

class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            message = "Hello from resource_limits_oom test! Server is running."
            self.wfile.write(bytes(message, "utf8"))
        except Exception as e:
            print(f"Error handling request: {e}")
            self.send_error(500, f"Internal server error: {e}")

if __name__ == '__main__':
    server_address = ('0.0.0.0', 8080)
    httpd = HTTPServer(server_address, SimpleHTTPRequestHandler)
    print(f'Server running on {server_address[0]}:{server_address[1]}')
    httpd.serve_forever()
