import threading
import time
import os
from http.server import HTTPServer, BaseHTTPRequestHandler

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(b'{"status":"ok","service":"aks-mcp-server"}')
    def log_message(self, format, *args):
        pass

def start_health():
    server = HTTPServer(('0.0.0.0', 8080), HealthHandler)
    print("Health server started on 0.0.0.0:8080", flush=True)
    server.serve_forever()

if __name__ == "__main__":
    print("Starting AKS MCP Server...", flush=True)
    t = threading.Thread(target=start_health, daemon=True)
    t.start()
    print("Health server running on :8080", flush=True)
    while True:
        time.sleep(30)
        print("MCP server alive", flush=True)
