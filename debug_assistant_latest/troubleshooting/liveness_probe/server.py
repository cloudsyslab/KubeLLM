import time
from http.server import SimpleHTTPRequestHandler, HTTPServer

time.sleep(2)  # Simulate slow startup

class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK")
        else:
            self.send_response(404)
            self.end_headers()

server = HTTPServer(("0.0.0.0", 8765), Handler)
server.serve_forever()
