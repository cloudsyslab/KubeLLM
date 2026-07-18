import yaml
from http.server import HTTPServer, BaseHTTPRequestHandler

payload = yaml.safe_dump({"status": "ok"})
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(payload.encode())
HTTPServer(("0.0.0.0", 8765), Handler).serve_forever()
