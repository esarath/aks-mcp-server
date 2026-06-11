from kubernetes import client, config
import json

def load_k8s():
    try:
        config.load_incluster_config()
    except:
        config.load_kube_config()

def get_argocd_apps():
    load_k8s()
    api = client.CustomObjectsApi()
    try:
        apps = api.list_namespaced_custom_object(
            "argoproj.io", "v1alpha1", "argocd", "applications"
        )
        result = []
        for app in apps["items"]:
            status = app.get("status", {})
            result.append({
                "name": app["metadata"]["name"],
                "sync": status.get("sync", {}).get("status", "Unknown"),
                "health": status.get("health", {}).get("status", "Unknown"),
                "repo": app["spec"]["source"]["repoURL"],
                "revision": status.get("sync", {}).get("revision", "")[:8]
            })
        return json.dumps(result, indent=2)
    except Exception as e:
        return f"Error: {str(e)}"

def sync_app(app_name):
    load_k8s()
    api = client.CustomObjectsApi()
    try:
        api.patch_namespaced_custom_object(
            "argoproj.io", "v1alpha1", "argocd",
            "applications", app_name,
            {"operation": {
                "initiatedBy": {"username": "mcp-server"},
                "sync": {"revision": "HEAD"}
            }}
        )
        return f"Sync triggered for {app_name}"
    except Exception as e:
        return f"Error: {str(e)}"

def rollback_app(app_name, revision):
    load_k8s()
    api = client.CustomObjectsApi()
    try:
        api.patch_namespaced_custom_object(
            "argoproj.io", "v1alpha1", "argocd",
            "applications", app_name,
            {"operation": {
                "initiatedBy": {"username": "mcp-server"},
                "sync": {"revision": str(revision)}
            }}
        )
        return f"Rollback triggered for {app_name} to revision {revision}"
    except Exception as e:
        return f"Error: {str(e)}"
