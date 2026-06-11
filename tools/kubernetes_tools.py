from kubernetes import client, config
import json

def load_k8s():
    try:
        config.load_incluster_config()
    except:
        config.load_kube_config()

def get_pods(namespace="production"):
    load_k8s()
    v1 = client.CoreV1Api()
    pods = v1.list_namespaced_pod(namespace)
    result = []
    for pod in pods.items:
        cs = pod.status.container_statuses or []
        result.append({
            "name": pod.metadata.name,
            "status": pod.status.phase,
            "ready": all(c.ready for c in cs),
            "restarts": sum(c.restart_count for c in cs),
            "node": pod.spec.node_name,
            "image": pod.spec.containers[0].image
        })
    return json.dumps(result, indent=2)

def get_deployments(namespace="production"):
    load_k8s()
    apps = client.AppsV1Api()
    deps = apps.list_namespaced_deployment(namespace)
    result = []
    for d in deps.items:
        result.append({
            "name": d.metadata.name,
            "desired": d.spec.replicas,
            "ready": d.status.ready_replicas or 0,
            "available": d.status.available_replicas or 0,
            "image": d.spec.template.spec.containers[0].image
        })
    return json.dumps(result, indent=2)

def describe_pod(pod_name, namespace="production"):
    load_k8s()
    v1 = client.CoreV1Api()
    try:
        pod = v1.read_namespaced_pod(pod_name, namespace)
        events = v1.list_namespaced_event(
            namespace,
            field_selector=f"involvedObject.name={pod_name}"
        )
        cs = pod.status.container_statuses or []
        result = {
            "name": pod.metadata.name,
            "node": pod.spec.node_name,
            "status": pod.status.phase,
            "containers": [
                {
                    "name": c.name,
                    "image": c.image,
                    "ready": s.ready if s else False,
                    "restarts": s.restart_count if s else 0
                }
                for c, s in zip(
                    pod.spec.containers,
                    cs or [None]*len(pod.spec.containers)
                )
            ],
            "events": [
                {
                    "type": e.type,
                    "reason": e.reason,
                    "message": e.message
                }
                for e in events.items[-5:]
            ]
        }
        return json.dumps(result, indent=2)
    except Exception as e:
        return f"Error: {str(e)}"

def get_pod_logs(pod_name, namespace="production", tail=50):
    load_k8s()
    v1 = client.CoreV1Api()
    try:
        logs = v1.read_namespaced_pod_log(
            pod_name, namespace, tail_lines=tail
        )
        return logs or "No logs found"
    except Exception as e:
        return f"Error: {str(e)}"

def scale_deployment(name, replicas, namespace="production"):
    load_k8s()
    apps = client.AppsV1Api()
    try:
        apps.patch_namespaced_deployment_scale(
            name, namespace, {"spec": {"replicas": replicas}}
        )
        return f"Scaled {name} to {replicas} replicas in {namespace}"
    except Exception as e:
        return f"Error: {str(e)}"

def get_nodes():
    load_k8s()
    v1 = client.CoreV1Api()
    nodes = v1.list_node()
    result = []
    for n in nodes.items:
        conds = {c.type: c.status for c in n.status.conditions}
        result.append({
            "name": n.metadata.name,
            "ready": conds.get("Ready") == "True",
            "cpu": n.status.capacity.get("cpu"),
            "memory": n.status.capacity.get("memory"),
            "version": n.status.node_info.kubelet_version
        })
    return json.dumps(result, indent=2)

def cluster_health():
    load_k8s()
    v1 = client.CoreV1Api()
    namespaces = ["production", "monitoring", "argocd", "kube-system"]
    summary = {}
    for ns in namespaces:
        try:
            pods = v1.list_namespaced_pod(ns)
            total = len(pods.items)
            running = sum(1 for p in pods.items if p.status.phase == "Running")
            summary[ns] = {
                "total": total,
                "running": running,
                "unhealthy": total - running
            }
        except:
            summary[ns] = "not found"
    return json.dumps(summary, indent=2)

def get_events(namespace="production"):
    load_k8s()
    v1 = client.CoreV1Api()
    events = v1.list_namespaced_event(namespace)
    warnings = [
        {
            "type": e.type,
            "reason": e.reason,
            "object": e.involved_object.name,
            "message": e.message,
            "count": e.count
        }
        for e in events.items
        if e.type == "Warning"
    ]
    return json.dumps(
        warnings[-10:] if warnings else [{"status": "No warnings"}],
        indent=2
    )
