import os
from http.server import HTTPServer, BaseHTTPRequestHandler

mode = os.environ["APP_MODE"]

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(f"mode={mode}".encode())

HTTPServer(("0.0.0.0", 8765), Handler).serve_forever()
