from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
import asyncio
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

from tools.kubernetes_tools import (
    get_pods, get_deployments, describe_pod,
    get_pod_logs, scale_deployment, get_nodes,
    cluster_health, get_events
)
from tools.prometheus_tools import query_prometheus, get_alerts
from tools.argocd_tools import get_argocd_apps, sync_app, rollback_app

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{"status":"ok","service":"aks-mcp-server"}')
        else:
            self.send_response(404)
            self.end_headers()
    def log_message(self, format, *args):
        pass

def start_health_server():
    server = HTTPServer(('0.0.0.0', 8080), HealthHandler)
    server.serve_forever()

app = Server("aks-mcp-server")

TOOLS = [
    Tool(name="get_pods",
         description="List all pods in a namespace with status and restarts",
         inputSchema={"type":"object","properties":{
             "namespace":{"type":"string","default":"production"}}}),
    Tool(name="get_deployments",
         description="List deployments with replica counts and image",
         inputSchema={"type":"object","properties":{
             "namespace":{"type":"string","default":"production"}}}),
    Tool(name="describe_pod",
         description="Get detailed pod info with events",
         inputSchema={"type":"object","required":["pod_name"],"properties":{
             "pod_name":{"type":"string"},
             "namespace":{"type":"string","default":"production"}}}),
    Tool(name="get_pod_logs",
         description="Get last N lines of pod logs",
         inputSchema={"type":"object","required":["pod_name"],"properties":{
             "pod_name":{"type":"string"},
             "namespace":{"type":"string","default":"production"},
             "tail":{"type":"integer","default":50}}}),
    Tool(name="scale_deployment",
         description="Scale a deployment to N replicas",
         inputSchema={"type":"object","required":["name","replicas"],"properties":{
             "name":{"type":"string"},
             "replicas":{"type":"integer"},
             "namespace":{"type":"string","default":"production"}}}),
    Tool(name="get_nodes",
         description="List cluster nodes with status and capacity",
         inputSchema={"type":"object","properties":{}}),
    Tool(name="cluster_health",
         description="Overall cluster health across all namespaces",
         inputSchema={"type":"object","properties":{}}),
    Tool(name="get_events",
         description="Get Warning events in a namespace",
         inputSchema={"type":"object","properties":{
             "namespace":{"type":"string","default":"production"}}}),
    Tool(name="query_prometheus",
         description="Run a PromQL query against Prometheus",
         inputSchema={"type":"object","required":["query"],"properties":{
             "query":{"type":"string"}}}),
    Tool(name="get_alerts",
         description="Get currently firing Prometheus alerts",
         inputSchema={"type":"object","properties":{}}),
    Tool(name="get_argocd_apps",
         description="List ArgoCD applications with sync and health status",
         inputSchema={"type":"object","properties":{}}),
    Tool(name="sync_app",
         description="Trigger ArgoCD sync for an application",
         inputSchema={"type":"object","required":["app_name"],"properties":{
             "app_name":{"type":"string"}}}),
    Tool(name="rollback_app",
         description="Rollback ArgoCD application to a revision",
         inputSchema={"type":"object","required":["app_name","revision"],"properties":{
             "app_name":{"type":"string"},
             "revision":{"type":"integer"}}}),
]

@app.list_tools()
async def list_tools():
    return TOOLS

@app.call_tool()
async def call_tool(name: str, arguments: dict):
    dispatch = {
        "get_pods":         lambda: get_pods(arguments.get("namespace","production")),
        "get_deployments":  lambda: get_deployments(arguments.get("namespace","production")),
        "describe_pod":     lambda: describe_pod(arguments["pod_name"],arguments.get("namespace","production")),
        "get_pod_logs":     lambda: get_pod_logs(arguments["pod_name"],arguments.get("namespace","production"),arguments.get("tail",50)),
        "scale_deployment": lambda: scale_deployment(arguments["name"],arguments["replicas"],arguments.get("namespace","production")),
        "get_nodes":        lambda: get_nodes(),
        "cluster_health":   lambda: cluster_health(),
        "get_events":       lambda: get_events(arguments.get("namespace","production")),
        "query_prometheus": lambda: query_prometheus(arguments["query"]),
        "get_alerts":       lambda: get_alerts(),
        "get_argocd_apps":  lambda: get_argocd_apps(),
        "sync_app":         lambda: sync_app(arguments["app_name"]),
        "rollback_app":     lambda: rollback_app(arguments["app_name"],arguments["revision"]),
    }
    fn = dispatch.get(name)
    result = fn() if fn else f"Unknown tool: {name}"
    return [TextContent(type="text", text=str(result))]

if __name__ == "__main__":
    t = threading.Thread(target=start_health_server, daemon=True)
    t.start()
    print("MCP server starting on port 8080...")
    asyncio.run(stdio_server(app))
