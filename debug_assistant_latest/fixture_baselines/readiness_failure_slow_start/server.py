import time
from http.server import HTTPServer, BaseHTTPRequestHandler

started = time.time()
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/ready":
            time.sleep(2)
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"ready")
        else:
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"ok")
HTTPServer(("0.0.0.0", 8080), Handler).serve_forever()
