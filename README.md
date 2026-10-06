# 🚀 Preview Environment Platform (preview-env-platform)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> **Automated, ephemeral, per-Pull-Request preview environments on Kubernetes using GitOps (Argo CD), GitHub Actions, Helm, and NGINX Ingress.**

---

## 🚦 Project Status
- **Done**: Application code (FastAPI backend, React frontend, PostgreSQL) and local Docker Compose orchestration.
- **In Progress**: Helm chart configuration, GitHub Actions CI pipelines, and Argo CD ApplicationSet GitOps integration.

---

## 📌 Overview

**preview-env-platform** is a production-grade, cost-free portfolio DevOps project that automates the lifecycle of ephemeral environments for software development teams.

### The Core Idea
Every time a developer opens a Pull Request (PR) on GitHub:
1. A temporary, fully isolated replica of the full application stack is provisioned in its own Kubernetes namespace (`pr-<number>`).
2. The environment is allocated its own dedicated PostgreSQL database and domain name (e.g. `http://pr-123.<CLUSTER_IP>.nip.io`).
3. When the PR is updated with new commits, the preview environment automatically syncs and updates.
4. When the PR is merged or closed, the entire namespace, database, and all associated Kubernetes resources are deleted automatically.

---

## 🏗️ Architecture

```
                                  +---------------------------------------+
                                  |            GitHub Repository          |
                                  |   (PR Opened / Updated / Closed)      |
                                  +---------------------------------------+
                                       |                             |
                       1. PR Trigger   |                             | 2. PR Webhook /
                                       v                             |    Polling
                    +-----------------------------+                  v
                    |    GitHub Actions CI        |       +---------------------+
                    | - Lint & Unit Test          |       |   Argo CD Server    |
                    | - Trivy Security Scan       |       |  (ApplicationSet    |
                    | - Build & Push Docker Image |       |   PR Generator)     |
                    |   to GHCR (tag: pr-<num>)   |       +---------------------+
                    +-----------------------------+                  |
                                       |                             | 3. Render Helm Chart &
                                       v                             |    Sync Manifests
                    +-----------------------------+                  v
                    | GitHub Container Registry   |       +----------------------------+
                    | (GHCR: ghcr.io/nitishhansa1)|       | Kubernetes Cluster         |
                    +-----------------------------+       | (kind / k3d / k3s)         |
                                                               |
                                                               +---> [ Namespace: pr-<num> ]
                                                                      |-- NGINX Ingress (pr-<num>.<IP>.nip.io)
                                                                      |-- FastAPI Backend Deployment
                                                                      |-- React Frontend Deployment
                                                                      |-- Dedicated Postgres StatefulSet
                                                                      |-- ResourceQuota & Limits
```

### Key Components
- **Sample App**: FastAPI (Python 3.11+) backend, React (Vite) frontend, PostgreSQL 16 database.
- **Containers**: Multi-stage Docker builds, non-root security contexts, minimal Alpine-based images.
- **Registry**: GitHub Container Registry (GHCR) with public/tokenless or read-token image pull.
- **CI Pipeline**: GitHub Actions for linting, testing, Trivy container scanning, building, and tagging images (`pr-<number>`).
- **Cluster Orchestration**: Local `kind` or `k3d` cluster (with `k3s` cloud migration readiness).
- **GitOps Engine**: Argo CD with `ApplicationSet` utilizing the Pull Request generator.
- **Packaging**: Single parametric Helm chart with templated overrides per PR namespace.
- **Ingress Controller**: NGINX Ingress Controller with dynamic wildcard `nip.io` routing.

---

## ⚙️ How It Works

1. **Pull Request Trigger**:
   - A developer creates PR `#42` on GitHub.
   - GitHub Actions runs unit tests, static code analysis, and Trivy vulnerability scans.
   - Upon test success, Docker images are built and pushed to GHCR with tag `pr-42`.

2. **GitOps Detection**:
   - Argo CD ApplicationSet continuously queries GitHub's Pull Request API (or receives GitHub webhooks).
   - It identifies PR `#42` is open and generates a new Argo CD Application targeting namespace `pr-42`.

3. **Cluster Deployment**:
   - Argo CD applies the Helm chart into namespace `pr-42`.
   - Helm creates:
     - Frontend Deployment (`pr-42` image tag) & ClusterIP Service.
     - Backend Deployment (`pr-42` image tag) & ClusterIP Service.
     - Dedicated PostgreSQL StatefulSet & PersistentVolumeClaim.
     - ResourceQuota to limit CPU/Memory usage and prevent cluster exhaustion.
     - Ingress rule with host `http://pr-42.<NODE_IP>.nip.io`.

4. **PR Notification**:
   - A secondary GitHub Action posts a comment on PR `#42` with the live preview link for QA, designers, and reviewers.

5. **Automated Teardown**:
   - When PR `#42` is merged or closed, the ApplicationSet removes the Application from the cluster.
   - Finalizers cascade-delete the `pr-42` namespace, freeing compute and storage.

---

## 📋 Prerequisites

Before running this project locally, ensure you have installed:
- [Docker](https://docs.docker.com/get-docker/) (v24.0+)
- [kubectl](https://kubernetes.io/docs/tasks/tools/) (v1.28+)
- [kind](https://kind.sigs.k8s.io/) or [k3d](https://k3d.io/)
- [Helm](https://helm.sh/docs/intro/install/) (v3.12+)
- [GitHub CLI (gh)](https://cli.github.com/) *(optional, for PR testing)*

---

## 🛠️ Local Setup

### 1. Clone the Repository
```bash
git clone https://github.com/nitishhansa1/preview-env-platform.git
cd preview-env-platform
```

### 2. Create the Local Kubernetes Cluster
Run the automated bootstrap script to spin up a `kind` cluster configured with ingress ports (80/443), NGINX Ingress Controller, and Argo CD:
```bash
chmod +x scripts/setup-kind.sh
./scripts/setup-kind.sh
```

### 3. Deploy Argo CD ApplicationSet
Apply the GitOps controller ApplicationSet definition:
```bash
kubectl apply -f argocd/applicationset.yaml
```

### 4. Run Smoke Tests
Verify connectivity and ingress routing:
```bash
chmod +x scripts/smoke-test.sh
./scripts/smoke-test.sh
```

---

## 🎬 Demo

*(Screenshots and walkthrough clips demonstrating PR creation, automated bot comments, live preview URLs, and automatic resource deletion upon merge).*

- **PR Bot Comment Example**:
  > 🚀 **Preview Environment Ready!**
  > - **URL**: [http://pr-42.127.0.0.1.nip.io](http://pr-42.127.0.0.1.nip.io)
  > - **Namespace**: `pr-42`
  > - **Commit**: `a1b2c3d`

---

## 💡 Problems I Hit and How I Fixed Them

| # | Problem Encountered | Root Cause | Solution & Fix |
|---|---------------------|------------|----------------|
| 1 | **GHCR `ImagePullBackOff`** | Ephemeral PR namespaces lacked container registry credentials. | Configured cluster-wide image pull secret or set GHCR package visibility to public for preview images. |
| 2 | **Orphaned PVCs on Teardown** | Kubernetes does not delete PVCs by default when deleting StatefulSets. | Enabled namespace deletion cascading in Argo CD application finalizers. |
| 3 | **GitHub API Rate Limiting** | Argo CD ApplicationSet polling GitHub API hit unauthenticated rate limits (60 req/hr). | Configured a GitHub Personal Access Token (PAT) / GitHub App token in the ApplicationSet generator secret. |
| 4 | **DNS Resolution Failure with `nip.io`** | Some local corporate DNS resolvers / ISPs block `nip.io` wildcard DNS resolution due to rebinding protection. | Added local `/etc/hosts` fallback and custom dnsmasq configuration guidelines. |
| 5 | **Noisy Neighbor / Resource Starvation** | Multiple concurrent PRs consumed all node CPU and memory. | Implemented strict `ResourceQuota` and default `LimitRange` per ephemeral PR namespace. |
