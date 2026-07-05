import http.server
import socketserver

Handler = http.server.SimpleHTTPRequestHandler

with socketserver.TCPServer(("127.0.0.1", 8765), Handler) as httpd:
    print("Serving on port 8765")
    httpd.serve_forever()
