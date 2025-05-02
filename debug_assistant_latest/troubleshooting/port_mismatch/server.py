import http.server
import socketserver

Handler = http.server.SimpleHTTPRequestHandler

with socketserver.TCPServer(("0.0.0.0", 8765), Handler) as httpd:
    print(f"Serving on port {8765}")
    httpd.serve_forever()