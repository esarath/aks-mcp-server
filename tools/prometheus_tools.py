import requests
import json
import os

PROM_URL = os.getenv(
    "PROMETHEUS_URL",
    "http://prometheus-operated.monitoring.svc.cluster.local:9090"
)

def query_prometheus(query):
    try:
        r = requests.get(
            f"{PROM_URL}/api/v1/query",
            params={"query": query},
            timeout=10
        )
        data = r.json()
        if data["status"] == "success":
            results = data["data"]["result"][:10]
            return json.dumps([
                {"metric": r["metric"], "value": r["value"][1]}
                for r in results
            ], indent=2)
        return f"Query failed: {data}"
    except Exception as e:
        return f"Prometheus unreachable: {str(e)}"

def get_alerts():
    try:
        r = requests.get(f"{PROM_URL}/api/v1/alerts", timeout=10)
        alerts = r.json()["data"]["alerts"]
        firing = [
            {
                "name": a["labels"].get("alertname"),
                "severity": a["labels"].get("severity"),
                "state": a["state"],
                "summary": a["annotations"].get("summary", "")
            }
            for a in alerts if a["state"] == "firing"
        ]
        return json.dumps(
            firing if firing else [{"status": "No active alerts"}],
            indent=2
        )
    except Exception as e:
        return f"Alerts error: {str(e)}"
