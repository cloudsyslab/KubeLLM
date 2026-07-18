import time
from http.server import HTTPServer, BaseHTTPRequestHandler

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/healthz":
            end = time.time() + 0.8
            while time.time() < end:
                pass
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"healthy")
        else:
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"ok")
HTTPServer(("0.0.0.0", 8080), Handler).serve_forever()
