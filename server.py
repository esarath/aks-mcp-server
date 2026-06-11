import threading
import asyncio
import json
from http.server import HTTPServer, BaseHTTPRequestHandler

from tools.kubernetes_tools import (
    get_pods, get_deployments, describe_pod,
    get_pod_logs, scale_deployment, get_nodes,
    cluster_health, get_events
)
from tools.prometheus_tools import query_prometheus, get_alerts
from tools.argocd_tools import get_argocd_apps, sync_app, rollback_app

# ── Health check server ───────────────────────────────────────────
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"status":"ok","service":"aks-mcp-server"}')
        else:
            self.send_response(404)
            self.end_headers()
    def log_message(self, format, *args):
        pass

def start_health_server():
    httpd = HTTPServer(('0.0.0.0', 8080), HealthHandler)
    print("Health server listening on :8080")
    httpd.serve_forever()

# ── Main ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Start health endpoint in background
    t = threading.Thread(target=start_health_server, daemon=True)
    t.start()

    print("AKS MCP Server starting...")
    print("Tools available: get_pods, get_deployments, describe_pod,")
    print("  get_pod_logs, scale_deployment, get_nodes, cluster_health,")
    print("  get_events, query_prometheus, get_alerts,")
    print("  get_argocd_apps, sync_app, rollback_app")

    # Keep container running
    import time
    while True:
        time.sleep(60)
        print("MCP server running...")
