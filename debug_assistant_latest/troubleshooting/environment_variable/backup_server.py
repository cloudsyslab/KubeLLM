import os
from http.server import HTTPServer, BaseHTTPRequestHandler

mode = os.getenv("APP_MODE")
if not mode:
    raise EnvironmentError("Missing required environment variable 'APP_MODE'")

# Create a simple server
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/":
            self.send_response(200)
            self.end_headers()
        elif self.path == "/env":
            self.send_response(200)
            self.end_headers()
            self.wfile.write(f"Running in {mode}".encode())
        else:
            self.send_response(404)
            self.end_headers()

print(f"Running in {mode}")
httpd = HTTPServer(("0.0.0.0", 8765), Handler)
httpd.serve_forever()
