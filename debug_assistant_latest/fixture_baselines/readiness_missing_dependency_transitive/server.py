from http.server import HTTPServer, BaseHTTPRequestHandler
from helper_config import STATUS_TEXT

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/ready":
            self.send_response(200)
            self.end_headers()
            self.wfile.write(str(STATUS_TEXT).encode())
        else:
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"ok")
HTTPServer(("0.0.0.0", 8080), Handler).serve_forever()
