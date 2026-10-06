# Architecture & System Design: Preview Environment Platform

## 1. System Vision & Objective
In modern engineering workflows, reviewing changes only on static code or staging environments introduces major bottlenecks:
- Staging environments suffer from queue contention and broken builds.
- Reviewers cannot interactively test UI, API behaviors, or database migrations in isolation.

**preview-env-platform** provisions an isolated, production-like ephemeral preview environment for every Pull Request and destroys it automatically on PR merge or closure.

---

## 2. End-to-End Component Flow

```
[ Developer ]
      │
      ├─ 1. Git Push / PR #101 ─────────────────────────┐
      │                                                 ▼
      │                                       [ GitHub Repository ]
      │                                                 │
      │                                                 ├─ Trigger CI
      │                                                 ▼
      │                                    [ GitHub Actions Workflow ]
      │                                    • Pytest & Node build
      │                                    • Trivy Vulnerability Scan
      │                                    • Build & Push: ghcr.io/...:pr-101
      │                                                 │
      ├─ 2. Argo CD Polling / Webhook ◄─────────────────┘
      ▼
[ Argo CD ApplicationSet ]
      │
      ├─ 3. Generates Application: preview-pr-101
      ├─ 4. Renders Helm Chart (overriding tag: pr-101)
      ▼
[ Kubernetes Cluster (kind / k3d) ]
      │
      ▼
[ Namespace: pr-101 ]
      ├── Ingress: pr-101.<IP>.nip.io
      │     ├── /api  ─► [ Backend Service:8000 ] ─► [ FastAPI Pod (pr-101) ]
      │     └── /     ─► [ Frontend Service:80 ] ─► [ React NGINX Pod (pr-101) ]
      │
      ├── Database: [ PostgreSQL StatefulSet (pr-101) ] ◄── Isolated Volume
      │
      └── Security & Governance:
            ├── ResourceQuota (Caps CPU, Mem, Pod count)
            └── Non-root Security Context (UID 10001 / 101)
```

---

## 3. Key Design Decisions

### A. Dedicated per-PR Database vs. Shared Database
- **Choice**: Dedicated PostgreSQL StatefulSet per PR namespace.
- **Rationale**: Isolates schema migrations, table alters, and test mutations completely, avoiding schema collisions between PRs.

### B. Pull Request Generator in ApplicationSet
- **Choice**: Native Argo CD `pullRequest` SCM generator.
- **Rationale**: Declarative GitOps model. Argo CD is the single source of truth for desired cluster state. When the PR closes on GitHub, Argo CD automatically prunes the corresponding Application and its namespace.

### C. Wildcard nip.io Ingress Routing
- **Choice**: NGINX Ingress Controller combined with `nip.io` wildcard domain mapping (`pr-<num>.<IP>.nip.io`).
- **Rationale**: Zero-cost, zero-DNS-configuration routing that maps any IP address to dynamic subdomains without requiring a registered public domain or cloud DNS provider.

### D. Security Hardening
- Containers run with non-root security contexts (`appuser` / `nginx`).
- ResourceQuotas strictly limit compute per namespace to prevent resource starvation.
- Trivy vulnerability scanner halts pipelines on Critical/High severity CVEs.
