import os
from http.server import HTTPServer, BaseHTTPRequestHandler

message = os.environ["APP_MESSAGE"]
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(message.encode())
HTTPServer(("0.0.0.0", 8080), Handler).serve_forever()
