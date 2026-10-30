# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.hephaestus.optimization.coordinator import CandidateState
    from src.hephaestus.optimization.policy import OptimizationPolicy

def _nonnegative_int(value: str) -> int:
    parsed = int(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("value must be non-negative")
    return parsed


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("value must be positive")
    return parsed


def _repository_base_for_cli(tenants_root: Path) -> Path:
    """Return the explicit invocation base for repository-relative contracts."""
    del tenants_root
    return Path(os.path.abspath(os.fspath(Path.cwd())))


def _default_optimize_workspace(policy: OptimizationPolicy, policy_path: Path) -> Path:
    """Place optimization outputs under the tenant's git-ignored evals directory."""
    import json as json_mod

    base = json_mod.loads(Path(policy.base_config).read_text(encoding="utf-8"))
    return Path("tenants") / str(base["tenant_id"]) / "evals" / "optimize" / policy_path.stem


def _val_score(candidate: CandidateState) -> float | None:
    return candidate.val.score if candidate.val is not None else None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Hephaestus prompt evaluation CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    eval_parser = subparsers.add_parser("eval", help="Evaluate one variant against one dataset")
    eval_parser.add_argument("--config", required=True, help="Path to eval config JSON")

    progress_parser = subparsers.add_parser("eval-progress", help="Check eval run progress")
    progress_parser.add_argument("--output-dir", required=True, help="Output directory of the eval run")
    progress_parser.add_argument("--json", action="store_true", dest="json_output", help="Output raw JSON")

    optimize_parser = subparsers.add_parser(
        "optimize",
        help="Run the headless prompt/parameter optimization loop (no meta agent)",
    )
    optimize_parser.add_argument("--policy", required=True, help="Path to optimization policy JSON")
    optimize_parser.add_argument(
        "--workspace",
        help="Directory for the ledger and eval outputs; defaults to "
        "tenants/<tenant_id>/evals/optimize/<policy-name>",
    )
    optimize_parser.add_argument("--resume", action="store_true", help="Continue the workspace's ledger")
    optimize_parser.add_argument(
        "--final-test",
        action="store_true",
        help="Evaluate baseline and best once on the test split after optimization stops",
    )
    optimize_parser.add_argument(
        "--max-iterations", type=_nonnegative_int, help="Override budget.max_iterations"
    )
    optimize_parser.add_argument("--role-model", help="Override roles.model")

    ui_parser = subparsers.add_parser("ui", help="Launch the local web UI to browse tenant outputs")
    ui_parser.add_argument(
        "--tenants-root",
        default="tenants",
        help="Path to the tenants directory (default: tenants)",
    )
    ui_parser.add_argument("--host", default="127.0.0.1", help="Bind host (default: 127.0.0.1)")
    ui_parser.add_argument("--port", type=int, default=8765, help="Bind port (default: 8765)")

    customer_data_parser = subparsers.add_parser(
        "customer-data",
        help="Pull, push, or remove local customer data for a tenant",
    )
    customer_data_subparsers = customer_data_parser.add_subparsers(
        dest="customer_data_command",
        required=True,
    )

    for subcommand_name in ("pull", "push", "remove-local"):
        subparser = customer_data_subparsers.add_parser(subcommand_name)
        subparser.add_argument("--tenant", required=True, help="Tenant id under tenants/<tenant_id>/")
        subparser.add_argument(
            "--scope",
            default="all",
            choices=("raw", "derived", "all"),
            help="Data scope: raw, derived, or all (default: all)",
        )
        subparser.add_argument(
            "--storage-config",
            default=None,
            help="Optional override path for tenant storage config JSON",
        )

    customer_data_subparsers.choices["push"].add_argument(
        "--force",
        action="store_true",
        help="Allow overwriting existing GCS objects.",
    )
    customer_data_subparsers.choices["remove-local"].add_argument(
        "--yes",
        action="store_true",
        help="Required confirmation for local data removal.",
    )

    memory_parser = subparsers.add_parser(
        "memory",
        help="Build runtime memory cards from evaluation assets built by `assets build`",
    )
    memory_subparsers = memory_parser.add_subparsers(
        dest="memory_command",
        required=True,
    )
    build_memory_parser = memory_subparsers.add_parser(
        "build",
        help="Compile trusted-only runtime memory cards (the default)",
    )
    build_memory_parser.add_argument("--tenant", required=True)
    build_memory_parser.add_argument(
        "--asset-id",
        required=True,
        help="Finished evaluation asset to use as the source",
    )
    build_memory_parser.add_argument("--memory-id", required=True)
    build_memory_parser.add_argument("--tenants-root", default="tenants")
    build_memory_parser.add_argument(
        "--model",
        help="Generation model; defaults to the model the source asset was built with",
    )
    build_memory_parser.add_argument(
        "--max-source-traces",
        type=_positive_int,
        default=5,
        help="Maximum supporting trusted traces supplied for each guideline",
    )
    additive_memory_parser = memory_subparsers.add_parser(
        "build-additive",
        help="Explicitly extend trusted cards with evidence from inferred training cases",
    )
    additive_memory_parser.add_argument("--tenant", required=True)
    additive_memory_parser.add_argument("--asset-id", required=True)
    additive_memory_parser.add_argument("--base-memory-id", required=True)
    additive_memory_parser.add_argument("--memory-id", required=True)
    additive_memory_parser.add_argument("--tenants-root", default="tenants")
    additive_memory_parser.add_argument("--model")
    additive_memory_parser.add_argument(
        "--include-inferred",
        action="store_true",
        required=True,
        help="Explicit consent to use the asset's inferred training cases",
    )
    additive_memory_parser.add_argument("--batch-size", type=_positive_int, default=8)
    additive_memory_parser.add_argument(
        "--max-additions-per-card",
        type=_positive_int,
        default=3,
    )

    assets_parser = subparsers.add_parser(
        "assets",
        help="Build evaluation datasets from agent traces and feedback",
    )
    assets_subparsers = assets_parser.add_subparsers(dest="assets_command", required=True)

    build_asset_parser = assets_subparsers.add_parser(
        "build",
        help="Build or resume an evaluation asset: observe, synthesize guidelines, write rubrics",
    )
    build_asset_parser.add_argument("--config", required=True, help="Path to the asset build config JSON")
    build_asset_parser.add_argument(
        "--workers", type=_positive_int, help="Override the number of concurrent model calls"
    )

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "eval":
        from src.hephaestus.runs.eval_runner import load_eval_config, run_evaluation

        config = load_eval_config(Path(args.config))
        results = run_evaluation(config)

        run_id_str = ""
        run_config_path = Path(config.output_dir) / "run_config.json"
        if run_config_path.exists():
            import json as _json

            rc = _json.loads(run_config_path.read_text(encoding="utf-8"))
            run_id_str = rc.get("run_id", "")
        if run_id_str:
            print(f"Run ID: {run_id_str}")
        print(f"Evaluated {len(results)} cases. Output dir: {config.output_dir}")
        return

    if args.command == "eval-progress":
        import dataclasses
        import json as json_mod

        from src.hephaestus.runs.progress import read_progress

        progress = read_progress(Path(args.output_dir))
        if progress is None:
            print(f"No progress file found in {args.output_dir}")
            return

        if args.json_output:
            print(json_mod.dumps(dataclasses.asdict(progress), indent=2))
        else:
            score_str = (
                f"{progress.avg_composite_score:.1f}"
                if progress.avg_composite_score is not None
                else "N/A"
            )
            run_id_line = f"Run ID: {progress.run_id}  " if progress.run_id else ""
            print(
                f"{run_id_line}"
                f"Status: {progress.status}  "
                f"Progress: {progress.completed_cases}/{progress.total_cases}  "
                f"Avg score: {score_str}"
            )
        return

    if args.command == "optimize":
        import json as json_mod
        import logging

        from src.hephaestus.optimization import load_policy, run_optimization

        policy = load_policy(Path(args.policy))
        if args.max_iterations is not None:
            policy.budget.max_iterations = args.max_iterations
        if args.role_model:
            policy.role_model = args.role_model
        workspace = (
            Path(args.workspace) if args.workspace else _default_optimize_workspace(policy, Path(args.policy))
        )
        optimization_logger = logging.getLogger("src.hephaestus.optimization")
        optimization_logger.setLevel(logging.INFO)
        optimization_logger.addHandler(logging.StreamHandler())

        result = run_optimization(policy, workspace, resume=args.resume, final_test=args.final_test)
        print(
            json_mod.dumps(
                {
                    "stop_reason": result.stop_reason,
                    "iterations": result.iterations,
                    "baseline": {"train": result.baseline.train.score, "val": _val_score(result.baseline)},
                    "best": {
                        "candidate_id": result.best.candidate_id,
                        "train": result.best.train.score,
                        "val": _val_score(result.best),
                    },
                    "test": {name: split["score"] for name, split in (result.test or {}).items()} or None,
                    "best_config": str(result.best_config_path),
                    "ledger": str(result.ledger_path),
                },
                indent=2,
            )
        )
        return

    if args.command == "ui":
        from src.hephaestus.webui import serve

        serve(
            Path(args.tenants_root),
            host=args.host,
            port=args.port,
            repository_base=_repository_base_for_cli(Path(args.tenants_root)),
        )
        return

    if args.command == "customer-data":
        from src.hephaestus.storage import (
            load_storage_config,
            pull_customer_data,
            push_customer_data,
            remove_local_customer_data,
        )

        storage_config_path = Path(args.storage_config) if args.storage_config else None
        config = load_storage_config(args.tenant, storage_config_path)

        if args.customer_data_command == "pull":
            summaries = pull_customer_data(config=config, scope=args.scope)
            for item in summaries:
                print(
                    f"Pulled {item['scope']} data from {item['gcs_uri']} to {item['local_path']}"
                )
            return

        if args.customer_data_command == "push":
            summaries = push_customer_data(config=config, scope=args.scope, force=args.force)
            for item in summaries:
                print(
                    f"Pushed {item['scope']} data from {item['local_path']} to {item['gcs_uri']}"
                )
            return

        if args.customer_data_command == "remove-local":
            summaries = remove_local_customer_data(
                config=config,
                scope=args.scope,
                require_yes=args.yes,
            )
            for item in summaries:
                print(f"Removed local {item['scope']} data at {item['local_path']}")
            return

        raise ValueError(f"Unsupported customer-data command: {args.customer_data_command}")

    if args.command == "memory":
        if args.memory_command == "build":
            import json as json_mod

            from src.hephaestus.memory_assets import build_memory_asset

            manifest = build_memory_asset(
                tenants_root=Path(args.tenants_root),
                tenant_id=args.tenant,
                source_asset_id=args.asset_id,
                memory_asset_id=args.memory_id,
                model=args.model,
                max_source_traces=args.max_source_traces,
            )
            print(json_mod.dumps(manifest, indent=2, sort_keys=True))
            return
        if args.memory_command == "build-additive":
            import json as json_mod

            from src.hephaestus.memory_evidence import build_additive_memory_asset

            manifest = build_additive_memory_asset(
                tenants_root=Path(args.tenants_root),
                tenant_id=args.tenant,
                source_asset_id=args.asset_id,
                base_memory_asset_id=args.base_memory_id,
                memory_asset_id=args.memory_id,
                model=args.model,
                batch_size=args.batch_size,
                max_additions_per_card=args.max_additions_per_card,
            )
            print(json_mod.dumps(manifest, indent=2, sort_keys=True))
            return
        raise ValueError(f"Unsupported memory command: {args.memory_command}")

    if args.command == "assets":
        if args.assets_command == "build":
            import json as json_mod

            from src.hephaestus.data_pipeline.build import build_asset
            from src.hephaestus.data_pipeline.config import AssetConfig

            config = AssetConfig.from_dict(json_mod.loads(Path(args.config).read_text(encoding="utf-8")))
            if args.workers is not None:
                config.workers = args.workers
            repository_root = Path.cwd()
            manifest = build_asset(config, repository_root=repository_root)
            asset_root = config.asset_root(repository_root)
            print(json_mod.dumps({"datasets": manifest["datasets"]}, indent=2, sort_keys=True))
            print(f"Review report: {asset_root / 'review.md'}")
            return

        raise ValueError(f"Unsupported assets command: {args.assets_command}")

    raise ValueError(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    main()
