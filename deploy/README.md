<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

# FAFO K8s deployment

Run FAFO evals on a Kubernetes cluster. Each run gets its own pod, and results
persist on a shared PVC.

## Prerequisites

- `kubectl` configured with cluster access
- `python3` available locally (used for config rewriting)
- PVC `csi-pvc-mounted` available in your target namespace (see
  [Namespace setup](#namespace-setup))
- `.env` file at the project root with API keys (copy your `.envrc` or fill in
  `deploy/.env.example`)

## Quick start

```bash
# From the repository root:

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

## How it works

1. **Pod creation.** Each run creates a dedicated pod named
   `hephaestus-<tenant_id>-<hash>`, with the PVC mounted at `/shared-storage`.
   One pod per job gives full isolation.
2. **Code sync.** `run_eval.sh` copies `src/`, `hephaestus/`, `pyproject.toml`,
   the relevant `tenants/<tid>/` directory, and `.env` to `/tmp/<run-name>/` on
   the pod in a single tar pipe. This workspace is ephemeral and per-run, so
   tenant data is re-synced on every run.
3. **Dependency install.** `pip install -e .` runs inside the pod. A marker file
   (`.deps_installed`) stores a hash of `pyproject.toml`; the install is skipped
   while the hash matches and repeated when `pyproject.toml` changes.
4. **Config rewriting.** Only `output_dir` is rewritten, to point at the PVC
   (`/shared-storage/heph-results/<run-name>/`), and `run_id` is set to the run
   name. All other paths stay relative and work unchanged.
5. **Results persistence.** Results are written to the PVC and survive pod
   restarts. `--collect` copies them to `local-results/<run-name>/` under the
   local repository root.
6. **Pod completion.** For detached runs, the eval-runner container's
   entrypoint watches the eval process by PID. When the eval exits, the
   container exits with the eval's exit code (0 = success, non-zero = failure),
   so the pod moves to `Succeeded` or `Failed`. Native K8s sidecars terminate
   automatically when the eval-runner container exits. Results stay on the PVC.

Secrets (`.env`) are copied to the pod's `/tmp/` and sourced at runtime. They
are not persisted to the PVC.

## Architecture

```
Local machine                              K8s Pod
+---------------------+                   +-------------------------------+
| hephaestus/         |  tar pipe         | /tmp/<run-name>/              |
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

## Run names

Each eval run has one name, `hephaestus-<tenant_id>-<hash>`, used for:

- **Pod name:** one dedicated pod per job.
- **Results directory:** `/shared-storage/heph-results/<run-name>/`.
- **Run metadata:** `.run_meta`, `.pid`, and `.completed` markers in the
  results directory.

The hash is base36 of the epoch seconds, so concurrent runs for the same tenant
get different hashes and separate pods, with no collisions. The same `run_id` is
recorded in `run_config.json` and `progress.json`.

## Cleanup and shutdown

Deleting a pod is safe: results persist on the PVC and survive pod deletion.

**Detached runs** move to a terminal pod phase (`Succeeded` or `Failed`) when
the eval completes. The `.completed` marker and all results remain on the PVC.

**Interactive runs** leave the pod running so you can inspect results. Delete it
manually when done:

```bash
kubectl -n $NAMESPACE delete pod hephaestus-<tenant_id>-<hash>
```

**Batch cleanup.** `--cleanup` deletes completed and crashed eval pods (phase
`Succeeded` or `Failed`). Pods older than the age threshold that have not
finished are listed as stale, with the command to delete them manually.

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

## Namespace setup

All scripts require `NAMESPACE`, and every `kubectl` command targets it. The
scripts exit with an error if it is not set.

```bash
export NAMESPACE=my-namespace
```

### PVC requirement

The scripts expect a PVC named `csi-pvc-mounted` in the target namespace. PVCs
are namespace-scoped: the cluster has an existing PVC in the `default`
namespace, but other namespaces cannot see it.

If your namespace already has a PVC named `csi-pvc-mounted`, no setup is needed.
Otherwise, create a new PV + PVC pair that points to the same underlying CSI
storage.

### Creating a PV + PVC for your namespace

Replace `<your-namespace>` with your namespace name:

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

Verify that the PVC binds:

```bash
kubectl -n <your-namespace> get pvc csi-pvc-mounted
# STATUS should be "Bound"
```

> **Critical:** the `volumeHandle` in the PV **must** match the volume handle
> your CSI driver uses to locate the backing directory on each node. An
> incorrect handle causes `FailedMount` errors, because the matching directory
> does not exist on the node filesystem.

### Shared storage

All namespaces set up this way share the same underlying storage at
`/shared-storage`, so eval results written from one namespace are visible to
pods in other namespaces. Run names include a timestamp to avoid collisions.

## Notes

- The pods use a generic Python image and install dependencies at runtime
  (~2-3 min on first run). A pre-built Docker image can replace this later for
  faster startup.
- To force a dependency reinstall, delete the marker:
  `kubectl -n $NAMESPACE exec <pod-name> -- rm /tmp/<run-name>/.deps_installed`
