<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

# FAFO K8s Deployment

Run FAFO evals on a Kubernetes cluster.

## Prerequisites

- `kubectl` configured with cluster access
- `python3` available locally (used for config rewriting)
- PVC `csi-pvc-mounted` available in your target namespace (see [Namespace Setup](#namespace-setup))
- `.env` file at the project root with API keys (copy your `.envrc` or fill in `deploy/.env.example`)

## Quick Start

```bash
# From the project root (projects/hephaestus/):

# 0. Set your target namespace (required)
export NAMESPACE=my-namespace

# 1. Run an eval (creates a dedicated pod automatically)
deploy/scripts/run_eval.sh --config tenants/<tenant_id>/configs/<config>.json

# 2. Run in background (survives disconnects)
deploy/scripts/run_eval.sh --config tenants/<tenant_id>/configs/<config>.json --detach

# 3. Check progress of a detached run
deploy/scripts/run_eval.sh --status hephaestus-<tenant_id>-<hash>

# 4. Tail logs
deploy/scripts/run_eval.sh --logs hephaestus-<tenant_id>-<hash>

# 5. Collect results locally
deploy/scripts/run_eval.sh --collect hephaestus-<tenant_id>-<hash>

# 6. Stop a detached run
deploy/scripts/run_eval.sh --stop hephaestus-<tenant_id>-<hash>

# 7. Clean up stale pods
deploy/scripts/run_eval.sh --cleanup
```

## How It Works

1. **Pod creation** — Each run creates a dedicated pod named `hephaestus-<tenant_id>-<hash>` with the PVC mounted at `/shared-storage`. One pod per job ensures full isolation.

2. **Code sync** — `run_eval.sh` copies `src/`, `hephaestus/`, `pyproject.toml`, the relevant `tenants/<tid>/` directory, and `.env` to `/tmp/<run-name>/` on the pod.

3. **Dependency install** — On first sync, `pip install -e .` is run inside the pod. Subsequent runs skip this step (a marker file tracks installation).

4. **Config rewriting** — Only `output_dir` is rewritten to point to the PVC (`/shared-storage/heph-results/<run-name>/`). All other paths remain relative and work unchanged.

5. **Results persistence** — Results are written to the PVC and survive pod restarts. Use `--collect` to copy them back to your local machine.

6. **Pod completion** — Detached runs exit their pod on completion (Succeeded if eval passed, Failed if it errored). Use `--cleanup` to delete terminal pods. Results remain on the PVC.

7. **Pod lifecycle** — The eval-runner container's entrypoint monitors the eval process via its PID. When the eval exits, the container exits with the eval's exit code (0 = success, non-zero = failure), transitioning the pod to `Succeeded` or `Failed`. Native K8s sidecars auto-terminate when the eval-runner container exits.

## Architecture

```
Local machine                              K8s Pod
+---------------------+                   +-------------------------------+
| hephaestus/         |  kubectl cp       | /tmp/<run-name>/              |
|   src/              | ───────────────>  |   src/  (code)                |
|   tenants/<tid>/    |                   |   tenants/<tid>/  (data)      |
|   pyproject.toml    |                   |   pyproject.toml              |
|   .env              |                   |   .env  (secrets)             |
|                     |                   |                               |
| deploy/scripts/     |                   | /shared-storage/heph-results/ |
|   run_eval.sh       |                   |   <run-name>/results.jsonl    |
|   launch_eval_pod.sh|                   |   <run-name>/summary.md       |
+---------------------+                   +-------------------------------+
                                          PVC: csi-pvc-mounted @ /shared-storage
```

## Naming Convention

Each eval run uses a unified name: `hephaestus-<tenant_id>-<hash>`

This name is used for:
- **Pod name** — one dedicated pod per job
- **Results directory** — `/shared-storage/heph-results/<run-name>/`
- **Run metadata** — `.run_meta`, `.pid`, `.completed` markers in the results dir

Concurrent runs for the same tenant get different hashes (base36 of epoch seconds) and separate pods — no collisions. The same `run_id` is recorded in `run_config.json` and `progress.json`.

## Cleanup

### Auto-cleanup (detached runs)

Detached runs transition to a terminal pod phase (Succeeded/Failed) after the eval completes. The `.completed` marker and all results remain on the PVC. Use `--cleanup` to delete terminal pods.

### Interactive runs

Interactive runs leave the pod running so you can inspect results. Delete manually when done:

```bash
kubectl -n $NAMESPACE delete pod hephaestus-<tenant_id>-<hash>
```

### Batch cleanup

Clean up stale eval pods (completed, crashed, or idle > 24h):

```bash
deploy/scripts/run_eval.sh --cleanup              # default: 24h age threshold
deploy/scripts/run_eval.sh --cleanup --age 12h    # custom threshold
```

## Configuration

| Env Variable | Default | Description |
|---|---|---|
| `PVC_NAME` | `csi-pvc-mounted` | PVC for persistent results |
| `IMAGE` | `python:3.11-slim` | Container image |
| `CPU_REQ` / `CPU_LIM` | 2 / 4 | CPU request / limit |
| `MEM_REQ` / `MEM_LIM` | 4Gi / 8Gi | Memory request / limit |
| `NAMESPACE` | **(required)** | Kubernetes namespace for all commands |

## Namespace Setup

All scripts require the `NAMESPACE` environment variable. Every `kubectl` command targets this namespace:

```bash
export NAMESPACE=my-namespace
```

The scripts will exit with an error if `NAMESPACE` is not set.

### PVC requirement

The scripts expect a PVC named `csi-pvc-mounted` in the target namespace. PVCs are namespace-scoped — the cluster has an existing PVC in the `default` namespace, but it is not visible from other namespaces.

If your namespace already has a PVC named `csi-pvc-mounted`, no extra setup is needed. Otherwise, you must create a new PV + PVC pair that points to the same underlying CSI storage.

### Creating a PV + PVC for your namespace

Replace `<your-namespace>` below with your actual namespace name:

```bash
kubectl apply -f - <<'EOF'
apiVersion: v1
kind: PersistentVolume
metadata:
  name: csi-pvc-volume-mounted-<your-namespace>
  annotations:
    pv.kubernetes.io/provisioned-by: your-csi-driver
spec:
  accessModes:
    - ReadWriteMany
  capacity:
    storage: 10Ti
  csi:
    driver: your-csi-driver
    volumeAttributes:
      mountPath: /csi-mounted-fs-path-data/pvc-your-volume-handle-here/
    volumeHandle: pvc-your-volume-handle-here
  persistentVolumeReclaimPolicy: Retain
  storageClassName: csi-mounted-fs-path-sc
  volumeMode: Filesystem
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: csi-pvc-mounted
  namespace: <your-namespace>
spec:
  accessModes:
    - ReadWriteMany
  resources:
    requests:
      storage: 10Gi
  storageClassName: csi-mounted-fs-path-sc
  volumeName: csi-pvc-volume-mounted-<your-namespace>
EOF
```

Verify the PVC binds:

```bash
kubectl -n <your-namespace> get pvc csi-pvc-mounted
# STATUS should be "Bound"
```

> **Critical**: The `volumeHandle` in the PV **must** match the actual volume handle used by your CSI driver to locate the backing directory on each node. Using an incorrect handle will cause `FailedMount` errors because the corresponding directory will not exist on the node filesystem.

### Shared storage

All namespaces that follow this setup share the same underlying storage at `/shared-storage`. This means eval results written by one namespace are visible to pods in other namespaces. Run names include a timestamp to avoid collisions.

## Shutting Down the Eval Pod

Detached eval pods auto-terminate on completion. For interactive runs, delete manually:

```bash
kubectl -n $NAMESPACE delete pod hephaestus-<tenant_id>-<hash>
```

This is safe — results are persisted on the PVC and survive pod deletion.

## Notes

- This uses a generic Python image with runtime dep installation (~2-3 min on first run). A pre-built Docker image can replace this later for faster startup.
- Code is synced to `/tmp/<run-name>/` (ephemeral, per-run) via a single tar pipe for speed. Tenant data is re-synced each run.
- Secrets (`.env`) are copied to the pod's `/tmp/` and sourced at runtime. They are not persisted to the PVC.
- Dependencies are automatically reinstalled when `pyproject.toml` changes (tracked via hash). To force reinstall, delete the marker: `kubectl -n $NAMESPACE exec <pod-name> -- rm /tmp/<run-name>/.deps_installed`
