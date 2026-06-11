import threading
import asyncio
import json
import sys
import os
from http.server import HTTPServer, BaseHTTPRequestHandler

# ── Health check ──────────────────────────────────────────────────
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type','application/json')
        self.end_headers()
        self.wfile.write(b'{"status":"ok"}')
    def log_message(self,f,*a): pass

def start_health():
    HTTPServer(('0.0.0.0',8080),HealthHandler).serve_forever()

# ── MCP over stdio ────────────────────────────────────────────────
from mcp.server.fastmcp import FastMCP

from tools.kubernetes_tools import (
    get_pods, get_deployments, describe_pod,
    get_pod_logs, scale_deployment, get_nodes,
    cluster_health, get_events
)
from tools.prometheus_tools import query_prometheus, get_alerts
from tools.argocd_tools import get_argocd_apps, sync_app, rollback_app

mcp = FastMCP("aks-cluster")

@mcp.tool()
def tool_get_pods(namespace: str = "production") -> str:
    """List all pods in a Kubernetes namespace with status and restarts"""
    return get_pods(namespace)

@mcp.tool()
def tool_get_deployments(namespace: str = "production") -> str:
    """List deployments with replica counts and current image"""
    return get_deployments(namespace)

@mcp.tool()
def tool_describe_pod(pod_name: str, namespace: str = "production") -> str:
    """Get detailed pod info including events and conditions"""
    return describe_pod(pod_name, namespace)

@mcp.tool()
def tool_get_pod_logs(pod_name: str, namespace: str = "production", tail: int = 50) -> str:
    """Get last N lines of logs from a pod"""
    return get_pod_logs(pod_name, namespace, tail)

@mcp.tool()
def tool_scale_deployment(name: str, replicas: int, namespace: str = "production") -> str:
    """Scale a Kubernetes deployment to specified replica count"""
    return scale_deployment(name, replicas, namespace)

@mcp.tool()
def tool_get_nodes() -> str:
    """List cluster nodes with Ready status and CPU/memory capacity"""
    return get_nodes()

@mcp.tool()
def tool_cluster_health() -> str:
    """Get overall cluster health summary across all namespaces"""
    return cluster_health()

@mcp.tool()
def tool_get_events(namespace: str = "production") -> str:
    """Get Warning events in a namespace for troubleshooting"""
    return get_events(namespace)

@mcp.tool()
def tool_query_prometheus(query: str) -> str:
    """Run a PromQL query against Prometheus and return results"""
    return query_prometheus(query)

@mcp.tool()
def tool_get_alerts() -> str:
    """Get currently firing Prometheus alerts with severity"""
    return get_alerts()

@mcp.tool()
def tool_get_argocd_apps() -> str:
    """List all ArgoCD applications with sync and health status"""
    return get_argocd_apps()

@mcp.tool()
def tool_sync_app(app_name: str) -> str:
    """Trigger ArgoCD sync for an application"""
    return sync_app(app_name)

@mcp.tool()
def tool_rollback_app(app_name: str, revision: int) -> str:
    """Rollback an ArgoCD application to a specific revision"""
    return rollback_app(app_name, revision)

if __name__ == "__main__":
    # If running as MCP stdio (called by Claude Desktop)
    if not sys.stdin.isatty():
        mcp.run(transport="stdio")
    else:
        # Running as K8s pod — start health server + keep alive
        t = threading.Thread(target=start_health, daemon=True)
        t.start()
        print("AKS MCP Server running on :8080")
        mcp.run(transport="stdio")
