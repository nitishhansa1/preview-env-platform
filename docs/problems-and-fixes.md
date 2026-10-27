# Troubleshooting Log: Real-World Problems & Fixes

This document records the technical hurdles, debugging steps, and architectural solutions implemented while developing the **preview-env-platform**.

---

### Issue 1: GitHub Container Registry (GHCR) `ImagePullBackOff` in Dynamic Namespaces
- **Symptom**: Pods in dynamically created `pr-<number>` namespaces failed to pull images from GHCR with `ErrImagePull` / `ImagePullBackOff` (401/403 Unauthorized).
- **Cause**: Kubernetes namespaces do not inherit `imagePullSecrets` from the `default` or `argocd` namespace.
- **Fix**:
  1. Option A: Changed GHCR container package visibility to **Public** for portfolio preview builds.
  2. Option B: Added a Kyverno or Argo CD pre-sync job that automatically replicates a cluster secret containing GHCR read tokens into newly spawned `pr-<number>` namespaces.

---

### Issue 2: Orphaned PersistentVolumeClaims (PVCs) on PR Teardown
- **Symptom**: When a PR was closed, Argo CD deleted the `StatefulSet`, but Kubernetes persistent volume claims remained allocated, consuming cluster storage.
- **Cause**: Kubernetes StatefulSet controller purposefully does not delete PVCs on StatefulSet deletion to prevent accidental data loss.
- **Fix**:
  Configured Argo CD ApplicationSet to manage the entire namespace with cascading deletion finalizers (`resources-finalizer.argocd.argoproj.io`), ensuring the entire namespace (including all PVCs, pods, and secrets) is cleanly destroyed on PR closure.

---

### Issue 3: GitHub API Rate Limiting on ApplicationSet Polling
- **Symptom**: Argo CD ApplicationSet stopped detecting newly opened PRs and logged `403 API rate limit exceeded`.
- **Cause**: Default unauthenticated GitHub API rate limit is 60 requests/hour per IP.
- **Fix**:
  Added a GitHub Personal Access Token (`GITHUB_TOKEN` or GitHub App) via a Kubernetes Secret referenced in the ApplicationSet `tokenRef` configuration, increasing rate limits to 5,000 requests/hour.

---

### Issue 4: DNS Rebinding Protection Blocking `nip.io`
- **Symptom**: In certain home or corporate routers, browsing to `pr-1.127.0.0.1.nip.io` failed to resolve.
- **Cause**: Modern DNS resolvers (like dnsmasq on OpenWrt / Pi-hole) block domain names that resolve to RFC 1918 / loopback IP addresses (DNS rebinding protection).
- **Fix**:
  Added fallback instructions to add entries to `/etc/hosts` (or `C:\Windows\System32\drivers\etc\hosts`) or use `curl -H "Host: pr-1.127.0.0.1.nip.io" http://127.0.0.1`.

---

### Issue 5: Noisy Neighbor Resource Contention
- **Symptom**: Opening multiple PRs simultaneously caused cluster node crashes with `OutOfMemory` (OOMKilled) or pod eviction.
- **Cause**: Without namespace resource boundaries, individual PRs could request unbounded CPU and RAM.
- **Fix**:
  Enforced a strict `ResourceQuota` in the Helm chart templates for every preview namespace, capping total compute per PR at 500m CPU and 512Mi RAM.

---

### Issue 6: Frontend Healthcheck Failure Due to IPv6 Localhost Resolution
- **Problem**: The frontend container healthcheck repeatedly failed with connection refused even though the NGINX web server was running and healthy.
- **Cause**: The healthcheck command queried `http://localhost:8080/healthz`. On modern Linux/Alpine containers, `localhost` resolved to the IPv6 loopback address (`::1`), while NGINX listened exclusively on IPv4 (`127.0.0.1`).
- **Fix**: Updated the container healthcheck in `app/frontend/Dockerfile` and `app/backend/Dockerfile` to explicitly query `http://127.0.0.1:8080/healthz` instead of `localhost`.
- **Lesson**: Never rely on `localhost` inside containerized healthchecks and exec probes; always bind and query explicit IPv4 loopback addresses (`127.0.0.1`) to avoid dual-stack resolution mismatches.

---

### Issue 7: Secret Mutation Across Argo CD Syncs in Offline Helm Rendering
- **Problem**: On every Argo CD reconciliation cycle, the PostgreSQL password was regenerated, causing backend database authentication failures and crash loops.
- **Cause**: Argo CD renders Helm charts offline using `helm template` without live cluster access. Therefore, Helm's `lookup` function always returns empty, causing `randAlphaNum` to generate a different random password on each sync.
- **Fix**: Replaced `lookup` and `randAlphaNum` with a deterministic, stable password generation pattern:
  `{{ printf "%s-%s" .Values.prNumber .Values.postgres.passwordSalt | sha256sum | trunc 24 }}`.
- **Lesson**: GitOps controllers rendering manifests offline cannot query cluster state during manifest generation. Use deterministic hashing from PR metadata or dedicated secret operators (e.g. External Secrets Operator) to guarantee secret stability.

---

### Issue 8: `nip.io` DNS Parsing Collision with PR Subdomains & Ingress Rewrite Stripping
- **Problem**: Opening `http://pr-29.127.0.0.1.nip.io:8080/` in the browser produced `ERR_CONNECTION_TIMED_OUT` ("This site can’t be reached"), and API requests routed through the Ingress returned `404 Not Found: {"detail":"Not Found"}`.
- **Cause**:
  1. **DNS Parsing Quirk**: `nip.io` extracts the first four dot-separated integer octets. In `pr-29.127.0.0.1.nip.io`, it parsed `29.127.0.0` as the IP address (a public DoD-allocated range) instead of `127.0.0.1`.
  2. **Port Mismatch**: Kind forwards host port `80` to the Ingress controller. Connecting to port `8080` fails unless a manual `kubectl port-forward` is active.
  3. **Path Prefix Stripping**: `ingress.yaml` used `nginx.ingress.kubernetes.io/rewrite-target: /$2` and regex `path: /api(/|$)(.*)`. This stripped `/api` and forwarded requests to FastAPI as `/applications` instead of `/api/applications`. Because FastAPI defines its routes at `/api/applications`, it responded with HTTP 404.
- **Fix**:
  1. Updated base domain to dashed notation `127-0-0-1.nip.io` (`pr-<num>.127-0-0-1.nip.io`) and added RFC 6761 `pr-<num>.localho.st` rules to the Ingress template.
  2. Removed `rewrite-target` and regex captures from `ingress.yaml`, using standard `pathType: Prefix` for `/api` (backend) and `/` (frontend).
  3. Pointed browsers to `http://pr-29.127-0-0-1.nip.io/` or `http://pr-29.localho.st/` on default HTTP port 80.
- **Lesson**: When generating dynamic DNS subdomains with `nip.io`, always use dashed IP notation (`127-0-0-1.nip.io`) or `.localho.st` to prevent subdomain numbers from colliding with IPv4 octet parsing. Avoid NGINX rewrite-target rules when the backend application already expects the path prefix.


