import http.server
import socketserver

Handler = http.server.SimpleHTTPRequestHandler

with socketserver.TCPServer(("0.0.0.0", 8000), Handler) as httpd:
    httpd.serve_forever()