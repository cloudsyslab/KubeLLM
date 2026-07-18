import http.server
import os
import socketserver

Handler = http.server.SimpleHTTPRequestHandler
host = os.environ.get("APP_HOST", "0.0.0.0")

with socketserver.TCPServer((host, 8765), Handler) as httpd:
    print(f"Serving on {host}:8765")
    httpd.serve_forever()
