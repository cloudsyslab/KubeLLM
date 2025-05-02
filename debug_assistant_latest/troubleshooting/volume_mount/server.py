import os
from http.server import HTTPServer, BaseHTTPRequestHandler

# Write to volume-mounted log
log_path = "/data/logs/app.log"
os.makedirs(os.path.dirname(log_path), exist_ok=True)
with open(log_path, "a") as f:
    f.write("Application started\n")

# Create a simple server
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/":
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Hello from volume-mounted server")
        elif self.path == "/log":
            self.send_response(200)
            self.end_headers()
            with open(log_path, "rb") as f:
                self.wfile.write(f.read())
        else:
            self.send_response(404)
            self.end_headers()

httpd = HTTPServer(("0.0.0.0", 8765), Handler)
httpd.serve_forever()
