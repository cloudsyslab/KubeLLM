import argparse
import http.server
import socketserver

parser = argparse.ArgumentParser()
parser.add_argument("--host", default="0.0.0.0")
args = parser.parse_args()

Handler = http.server.SimpleHTTPRequestHandler

with socketserver.TCPServer((args.host, 8765), Handler) as httpd:
    print(f"Serving on {args.host}:8765")
    httpd.serve_forever()
