# aks-infra
# ☸️ Production-Grade AKS PoC 

> **Built by:** Sarath Babu | Senior DevOps & Cloud Infrastructure Engineer  
> **Live URL:** http://20.242.133.71  
> **Cluster:** aks-kongs-poc | Kubernetes v1.34.8 | Azure eastus | 2x Standard_D2s_v7

---

## 📋 Table of Contents

- [Architecture Overview](#architecture-overview)
- [Technology Stack](#technology-stack)
- [Repository Structure](#repository-structure)
- [Prerequisites](#prerequisites)
- [Phase-by-Phase Deployment](#phase-by-phase-deployment)
- [CI/CD Pipeline Flow](#cicd-pipeline-flow)
- [GitOps Flow](#gitops-flow)
- [Observability](#observability)
- [Security](#security)
- [Troubleshooting Reference](#troubleshooting-reference)
- [Cluster Management](#cluster-management)
- [Quick Reference](#quick-reference)

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     AZURE SUBSCRIPTION                          │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │                 rg-kongs-poc (eastus)                      │ │
│  │  VNet: 10.0.0.0/16  ┌──────────────────────────────────┐ │ │
│  │  Subnet: 10.0.1.0/24│       AKS: aks-kongs-poc          │ │ │
│  │                      │       K8s v1.34.8                  │ │ │
│  │                      │  ┌──────────┐  ┌──────────────┐  │ │ │
│  │                      │  │  system  │  │     apps     │  │ │ │
│  │                      │  │  D2s_v7  │  │   D2s_v7     │  │ │ │
│  │                      │  │  1 node  │  │   1 node     │  │ │ │
│  │                      │  └──────────┘  └──────────────┘  │ │ │
│  │                      │  production  → web-app + postgres  │ │ │
│  │                      │  argocd      → GitOps engine       │ │ │
│  │                      │  monitoring  → Prometheus+Grafana  │ │ │
│  │                      └──────────────────────────────────┘ │ │
│  │  Log Analytics: law-kongs-poc (Container Insights)         │ │
│  └───────────────────────────────────────────────────────────┘ │
│  ┌─────────────┐                                               │
│  │  rg-tfstate │ → satfstatekongs001 (Terraform remote state)  │
│  └─────────────┘                                               │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🛠️ Technology Stack

| Layer | Technology | Version / Detail |
|---|---|---|
| Cloud | Microsoft Azure | eastus region |
| Kubernetes | AKS | v1.34.8 (non-LTS) |
| IaC | Terraform + AzureRM | v1.9.8 + v4.x |
| CI Pipeline | GitHub Actions (OIDC) | ARM_USE_OIDC=true |
| GitOps | ArgoCD | v2.12 app-of-apps |
| Registry | Docker Hub | esarathmails/web-app |
| Web Server | NGINX | 1.27-alpine |
| Database | PostgreSQL | 15-alpine StatefulSet |
| Observability | kube-prometheus-stack | Prometheus v3 + Grafana v11 |
| Azure Monitor | Container Insights | Log Analytics |
| Security | RBAC + Calico + OPA | Gatekeeper v3.17 |
| VM Size | Standard_D2s_v7 | 2 vCPU, 8GB RAM |
| OS Disk | Managed SSD | 128GB |

---

## 📁 Repository Structure

```
esarath/aks-infra
├── backend.tf        # Remote state: satfstatekongs001/tfstate/poc/aks.tfstate
├── variables.tf      # K8s 1.34, Standard_D2s_v7, eastus
├── main.tf           # VNet, AKS cluster+nodepools, Log Analytics
├── outputs.tf        # cluster name, RG, OIDC issuer, kube_config
├── .gitignore        # Excludes .terraform/, tfplan, *.tfstate
└── .github/workflows/terraform.yml

esarath/gitops-config
├── apps/
│   ├── root-app.yaml       # Bootstraps everything
│   ├── web-app.yaml        # selfHeal+prune=true
│   └── postgres.yaml       # selfHeal=true, prune=false
├── web-app/
│   ├── namespace.yaml
│   ├── deployment.yaml     # Auto-updated by CI with SHA tag
│   └── service.yaml        # LoadBalancer: 20.242.133.71
└── postgres/
    ├── statefulset.yaml    # PGDATA subdir fix
    ├── service.yaml
    └── secret.yaml         # Placeholder — real secret via kubectl

esarath/web-app
├── src/index.html          # Platform status dashboard
├── Dockerfile              # FROM nginx:1.27-alpine
└── .github/workflows/build-deploy.yml
```

---

## ✅ Prerequisites

```
Azure:
  Subscription ID:  7908ea24-a708-4291-be15-98426e3e9ca5
  Tenant ID:        466259fe-31da-408e-8f34-2c1e0d5a1307

GitHub:
  Account:   esarath
  Repos:     aks-infra, gitops-config, web-app
  PAT:       repo + workflow scopes required

Docker Hub:
  Username:  esarathmails
  Use Access Token (not password)

Terminal: Azure Cloud Shell (shell.azure.com)
  All tools pre-installed except ArgoCD CLI (see Phase 0)
```

---

## 🚀 Phase-by-Phase Deployment

### Phase 0 — Environment Setup

```bash
# Install ArgoCD CLI (no sudo in Cloud Shell)
mkdir -p ~/bin
curl -sSL -o ~/bin/argocd \
  https://github.com/argoproj/argo-cd/releases/latest/download/argocd-linux-amd64
chmod +x ~/bin/argocd
echo 'export PATH=$HOME/bin:$PATH' >> ~/.bashrc
export PATH=$HOME/bin:$PATH

# Create port-forward restart script
cat > ~/start-portforwards.sh << 'EOF'
#!/bin/bash
export PATH=$HOME/bin:$PATH
pkill -f "port-forward" 2>/dev/null && sleep 2
kubectl proxy --port=8001 --address=0.0.0.0 --accept-hosts='.*' > /tmp/proxy.log 2>&1 &
kubectl port-forward svc/argocd-server -n argocd 8080:443 > /tmp/argocd.log 2>&1 &
sleep 5
echo "Grafana: http://localhost:8001/api/v1/namespaces/monitoring/services/monitoring-grafana:80/proxy/"
echo "ArgoCD:  https://localhost:8080"
curl -s http://localhost:8001/api/v1/namespaces/monitoring/services/monitoring-grafana:80/proxy/api/health | grep database
EOF
chmod +x ~/start-portforwards.sh
```

> **EVERY new Cloud Shell session:** run `export PATH=$HOME/bin:$PATH && ~/start-portforwards.sh`

---

### Phase 1 — Azure Login & Setup

```bash
az login
az account set --subscription 7908ea24-a708-4291-be15-98426e3e9ca5

az group create --name rg-kongs-poc --location eastus
az group create --name rg-tfstate --location eastus

az storage account create --name satfstatekongs001 \
  --resource-group rg-tfstate --sku Standard_LRS --location eastus
az storage container create --name tfstate --account-name satfstatekongs001

# Service Principal
az ad app create --display-name gha-kongs-deployer
# SAVE appId → AZURE_CLIENT_ID

az ad sp create --id <APP_ID>
# SAVE id (objectId) → for role assignment only

az role assignment create --role 'Contributor' \
  --assignee-object-id <SP_OBJECT_ID> \
  --assignee-principal-type ServicePrincipal \
  --scope /subscriptions/7908ea24-a708-4291-be15-98426e3e9ca5

# OIDC federated credentials
az ad app federated-credential create --id <APP_ID> --parameters '{
  "name":"gha-aks-infra-main",
  "issuer":"https://token.actions.githubusercontent.com",
  "subject":"repo:esarath/aks-infra:ref:refs/heads/main",
  "audiences":["api://AzureADTokenExchange"]}'

az ad app federated-credential create --id <APP_ID> --parameters '{
  "name":"gha-webapp-main",
  "issuer":"https://token.actions.githubusercontent.com",
  "subject":"repo:esarath/web-app:ref:refs/heads/main",
  "audiences":["api://AzureADTokenExchange"]}'
```

> **WHY separate rg-tfstate?**
> Destroying rg-kongs-poc does NOT destroy Terraform state.
> Different lifecycle, different RBAC, cleaner cost reporting.

---

### Phase 2 — GitHub Secrets

**aks-infra repo** (Settings → Secrets → Actions):
```
AZURE_CLIENT_ID       = <appId>
AZURE_TENANT_ID       = 466259fe-31da-408e-8f34-2c1e0d5a1307
AZURE_SUBSCRIPTION_ID = 7908ea24-a708-4291-be15-98426e3e9ca5
```

**web-app repo** (above + these):
```
DOCKERHUB_USERNAME = esarathmails
DOCKERHUB_TOKEN    = <Docker Hub Access Token>
GITOPS_PAT         = <GitHub PAT: repo + workflow scopes>
```

> **PAT must have `repo` AND `workflow` scopes.**
> After generating: `git remote set-url origin https://esarath:<TOKEN>@github.com/esarath/REPO.git`

---

### Phase 3 — Terraform + AKS

```bash
cd ~/aks-infra
terraform init
terraform plan -out=tfplan
terraform apply tfplan

# If rg-kongs-poc already exists (created manually):
terraform import azurerm_resource_group.rg \
  /subscriptions/7908ea24-a708-4291-be15-98426e3e9ca5/resourceGroups/rg-kongs-poc
terraform plan -out=tfplan && terraform apply tfplan

az aks get-credentials --resource-group rg-kongs-poc \
  --name aks-kongs-poc --overwrite-existing
kubectl get nodes
```

**Critical Terraform settings for Azure free tier:**
```hcl
kubernetes_version = "1.34"      # 1.31/1.32 = LTS-only (Premium required)
vm_size = "Standard_D2s_v7"      # Standard_B not available in eastus
os_disk_type = "Managed"         # D2s_v7 has no local temp disk
os_disk_size_gb = 128            # Minimum for AKS 1.34 managed disk

upgrade_settings {               # MANDATORY in AzureRM v4.x
  max_surge = "10%"
}
```

---

### Phase 4 — GitHub Actions Terraform CI/CD

**Critical: ARM env vars at JOB level in terraform.yml:**
```yaml
jobs:
  terraform:
    runs-on: ubuntu-latest
    env:
      ARM_CLIENT_ID:       ${{ secrets.AZURE_CLIENT_ID }}
      ARM_TENANT_ID:       ${{ secrets.AZURE_TENANT_ID }}
      ARM_SUBSCRIPTION_ID: ${{ secrets.AZURE_SUBSCRIPTION_ID }}
      ARM_USE_OIDC:        "true"
    steps:
    - uses: azure/login@v2.3.0
      with:
        client-id: ${{ secrets.AZURE_CLIENT_ID }}
        tenant-id: ${{ secrets.AZURE_TENANT_ID }}
        subscription-id: ${{ secrets.AZURE_SUBSCRIPTION_ID }}
```

> AzureRM v4.x refuses `az login` SP session. ARM_USE_OIDC=true makes Terraform do its own OIDC exchange.

---

### Phase 5 — Web App + CI Pipeline

```bash
cd ~/web-app
git add . && git commit -m "feat: initial web app" && git push origin main
# Pipeline: build image → push to Docker Hub → update gitops-config deployment.yaml
```

---

### Phase 6 — GitOps Manifests

```bash
cd ~/gitops-config
git add . && git commit -m "feat: initial manifests" && git push origin main
```

**Critical fix in postgres/statefulset.yaml:**
```yaml
env:
- name: PGDATA
  value: /var/lib/postgresql/data/pgdata
# Azure Disk creates lost+found at mount root blocking PostgreSQL initdb
```

**postgres/secret.yaml in git — placeholder only:**
```yaml
data:
  POSTGRES_PASSWORD: UExBQ0VIT0xERVI=  # placeholder
  POSTGRES_USER: UExBQ0VIT0xERVI=      # placeholder
  POSTGRES_DB: UExBQ0VIT0xERVI=        # placeholder
# Real secret created via kubectl (never committed to git)
```

---

### Phase 7 — ArgoCD Bootstrap

```bash
kubectl create namespace argocd
kubectl apply -n argocd \
  -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
kubectl wait --for=condition=available deployment/argocd-server \
  -n argocd --timeout=300s

# Get admin password
kubectl -n argocd get secret argocd-initial-admin-secret \
  -o jsonpath='{.data.password}' | base64 -d && echo

# Register repo via kubectl Secret (reliable — no gRPC issues)
kubectl apply -f - <<EOF
apiVersion: v1
kind: Secret
metadata:
  name: gitops-config-repo
  namespace: argocd
  labels:
    argocd.argoproj.io/secret-type: repository
type: Opaque
stringData:
  type: git
  url: https://github.com/esarath/gitops-config
  username: esarath
  password: <GITOPS_PAT>
EOF

# Create production namespace + real PostgreSQL secret
kubectl create namespace production
kubectl create secret generic postgres-secret \
  --from-literal=POSTGRES_PASSWORD=KongsP0cDB#2025 \
  --from-literal=POSTGRES_USER=appuser \
  --from-literal=POSTGRES_DB=appdb \
  --namespace production

# Deploy root app
kubectl apply -f \
  https://raw.githubusercontent.com/esarath/gitops-config/main/apps/root-app.yaml

# Verify
kubectl get applications -n argocd
kubectl get pods -n production
```

> **After any rollback:** re-enable auto-sync:
> `argocd app set web-app --sync-policy automated --auto-prune --self-heal`

---

### Phase 8 — Observability

```bash
helm repo add prometheus-community \
  https://prometheus-community.github.io/helm-charts && helm repo update

helm install monitoring prometheus-community/kube-prometheus-stack \
  --namespace monitoring --create-namespace \
  --set prometheus.prometheusSpec.retention=7d \
  --set grafana.adminPassword=GrafanaAdmin@2025 \
  --set grafana.service.type=ClusterIP \
  --set alertmanager.enabled=false \
  --set nodeExporter.enabled=true \
  --set kubeStateMetrics.enabled=true

# Access via kubectl proxy
# (Free tier max 3 public IPs already used by AKS LB + web-app + ArgoCD)
kubectl proxy --port=8001 --address=0.0.0.0 --accept-hosts='.*' &

# Grafana URL (open in Cloud Shell Web Preview → port 8001, then add path):
# /api/v1/namespaces/monitoring/services/monitoring-grafana:80/proxy/
# Login: admin / GrafanaAdmin@2025

# Prometheus URL:
# /api/v1/namespaces/monitoring/services/monitoring-kube-prometheus-prometheus:9090/proxy/

# Import dashboards: 15760, 1860, 13770, 14584
```

---

## 🔄 CI/CD Pipeline Flow

```
git push → web-app/main
    ↓
GitHub Actions:
  Job 1: docker build + push → esarathmails/web-app:<SHA> + :latest
    ↓
  Job 2: update gitops-config/web-app/deployment.yaml → git push
    ↓
ArgoCD: detects drift → auto-sync → AKS rolling update
    ↓
Live: http://20.242.133.71  (~3-5 min, zero downtime)
```

---

## 🎯 GitOps Flow

```
gitops-config/apps/root-app.yaml  ← ONE apply bootstraps everything
  ├── web-app   (selfHeal=true, prune=true)   → deployment + service
  └── postgres  (selfHeal=true, prune=false)  → statefulset + service
```

**Self-healing demo:**
```bash
kubectl scale deployment web-app --replicas=0 -n production
# ArgoCD restores within 90 seconds
```

---

## 📊 Observability

| Dashboard ID | Name |
|---|---|
| 15760 | Kubernetes Cluster Overview |
| 1860 | Node Exporter Full |
| 13770 | Kubernetes Pods |
| 14584 | ArgoCD |

**Alert Rules:**
```
NodeMemoryLow:       memory < 15%   5m  warning
PodCrashLoopBackOff: crash looping  2m  critical
NodeCPUHigh:         CPU > 80%      5m  warning
```

---

## 🔐 Security

```bash
# RBAC — developer read-only role
kubectl apply -f <rbac-manifest>

# Network Policies — default deny + selective allow
# Allow web port 80, web→postgres port 5432, DNS port 53

# OPA Gatekeeper — enforce resource limits
kubectl apply -f \
  https://raw.githubusercontent.com/open-policy-agent/gatekeeper/v3.17.0/deploy/gatekeeper.yaml
```

---

## 🔧 Troubleshooting Reference

| Error | Root Cause | Fix |
|---|---|---|
| `K8sVersionNotSupported` 1.31/1.32 | LTS-only tier | Use `1.34` |
| `Standard_B2s not allowed` | Free tier restriction | Use `Standard_D2s_v7` |
| `VMSizeDoesNotSupportEphemeralOS` | No temp disk on D2s_v7 | `os_disk_type=Managed`, `128GB` |
| Missing `upgrade_settings` | Mandatory AzureRM v4.x | Add `upgrade_settings { max_surge="10%" }` |
| `terraform import` needed | RG pre-created via CLI | `terraform import azurerm_resource_group.rg ...` |
| `No subscriptions found` | Wrong CLIENT_ID or missing ARM vars | ARM_USE_OIDC=true at job level |
| `Unsupported auth-type WORKLOAD_IDENTITY` | Invalid value | Remove auth-type, use azure/login@v2.3.0 |
| `CLI SP auth not supported` | AzureRM v4.x refuses CLI SP | ARM_USE_OIDC=true |
| `workflow scope refused` | PAT missing scope | Regenerate PAT: repo + workflow |
| ArgoCD gRPC timeout | Cloud Shell instability | Register repo via kubectl Secret |
| Postgres CrashLoopBackOff | lost+found blocks initdb | PGDATA subdir env var |
| `illegal base64` in ArgoCD | Placeholder in secret.yaml | Commit real base64 values |
| `PublicIPCountLimitReached` | Free tier max 3 IPs | ClusterIP + kubectl proxy |
| ArgoCD auto-sync off | Rollback disables it | Re-enable via CLI or UI |
| Port-forward dies | Cloud Shell timeout | Run `~/start-portforwards.sh` |

**Health check:**
```bash
kubectl get nodes
kubectl get pods -A | grep -v Running | grep -v Completed
kubectl get applications -n argocd
curl http://20.242.133.71
```

---

## 🔄 Cluster Management

```bash
# Stop (save credits)
az aks stop --resource-group rg-kongs-poc --name aks-kongs-poc

# Start + reconnect
az aks start --resource-group rg-kongs-poc --name aks-kongs-poc
az aks get-credentials --resource-group rg-kongs-poc \
  --name aks-kongs-poc --overwrite-existing
export PATH=$HOME/bin:$PATH
~/start-portforwards.sh

# Destroy everything
cd ~/aks-infra && terraform destroy -auto-approve
az group delete --name rg-kongs-poc --yes --no-wait
az group delete --name rg-tfstate --yes --no-wait
```

---

## 📌 Quick Reference

```
Cluster:          aks-kongs-poc | rg-kongs-poc | eastus | K8s v1.34.8
Web App:          http://20.242.133.71
Grafana:          localhost:8001/api/v1/namespaces/monitoring/services/monitoring-grafana:80/proxy/
Prometheus:       localhost:8001/api/v1/namespaces/monitoring/services/monitoring-kube-prometheus-prometheus:9090/proxy/
ArgoCD:           https://localhost:8080
ArgoCD password:  kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath='{.data.password}' | base64 -d
Grafana login:    admin / GrafanaAdmin@2025
Docker Hub:       esarathmails/web-app
Terraform state:  satfstatekongs001/tfstate/poc/aks.tfstate
```

---

## 👤 Author

**Sarath Babu** | Senior DevOps & Cloud Infrastructure Engineer | Bengaluru  
**Certifications:** CKA | AZ-305 | AZ-104 | RHCE | DO280  
**GitHub:** [esarath](https://github.com/esarath) | **Docker Hub:** esarathmails

*Production-pattern AKS PoC for Kongsberg Digital Senior Infrastructure Engineer role.*

