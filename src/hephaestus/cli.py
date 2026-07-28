# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import argparse
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Hephaestus prompt evaluation CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    eval_parser = subparsers.add_parser("eval", help="Evaluate one variant against one dataset")
    eval_parser.add_argument("--config", required=True, help="Path to eval config JSON")

    progress_parser = subparsers.add_parser("eval-progress", help="Check eval run progress")
    progress_parser.add_argument("--output-dir", required=True, help="Output directory of the eval run")
    progress_parser.add_argument("--json", action="store_true", dest="json_output", help="Output raw JSON")

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

    assets_parser = subparsers.add_parser(
        "assets",
        help="Create generic evaluation assets from prepared tenant-local data",
    )
    assets_subparsers = assets_parser.add_subparsers(dest="assets_command", required=True)

    intent_parser = assets_subparsers.add_parser(
        "intent-inventory",
        help="Cluster prepared intent records and match them to trusted intents",
    )
    intent_parser.add_argument("--records", required=True, help="Prepared intent-record JSONL")
    intent_parser.add_argument("--trusted-intents", required=True, help="Trusted intent JSONL")
    intent_parser.add_argument("--output-dir", required=True, help="Output directory")
    intent_parser.add_argument("--id-field", required=True, help="Dot path for record id")
    intent_parser.add_argument(
        "--text-field",
        action="append",
        required=True,
        help="Dot path to include in canonical intent text; repeatable",
    )
    intent_parser.add_argument("--route-field", default=None, help="Optional dot path for route")
    intent_parser.add_argument("--group-field", default=None, help="Optional dot path for group id")
    intent_parser.add_argument(
        "--vectorizer",
        choices=("tfidf", "openai"),
        default="openai",
        help="Vectorizer for clustering and matching (default: openai)",
    )
    intent_parser.add_argument("--embedding-model", default="text-embedding-3-small")
    intent_parser.add_argument("--embedding-batch-size", type=int, default=128)
    intent_parser.add_argument("--embedding-timeout-seconds", type=int, default=300)
    intent_parser.add_argument("--embedding-max-retries", type=int, default=3)
    intent_parser.add_argument("--embedding-retry-backoff-seconds", type=int, default=2)
    intent_parser.add_argument("--similarity-threshold", type=float, default=0.35)
    intent_parser.add_argument("--match-threshold", type=float, default=0.35)
    intent_parser.add_argument("--min-trusted-examples", type=int, default=1)
    intent_parser.add_argument("--min-trusted-groups", type=int, default=0)
    intent_parser.add_argument("--large-cluster-size", type=int, default=0)
    intent_parser.add_argument("--min-trusted-examples-for-large-cluster", type=int, default=0)
    intent_parser.add_argument("--max-unlabeled-to-trusted-ratio", type=float, default=None)

    assemble_parser = assets_subparsers.add_parser(
        "assemble",
        help="Assemble versioned FAPO split files from prepared case JSONL",
    )
    assemble_parser.add_argument("--trusted-cases", required=True, help="Trusted FAPO cases JSONL")
    assemble_parser.add_argument("--synthetic-cases", required=True, help="Synthetic FAPO cases JSONL")
    assemble_parser.add_argument("--output-dir", required=True, help="Output directory")
    assemble_parser.add_argument("--dataset-version", required=True, help="Dataset version label")
    assemble_parser.add_argument("--regression-cases", default=None, help="Regression FAPO cases JSONL")
    assemble_parser.add_argument("--triage-cases", default=None, help="Triage-hold FAPO cases JSONL")
    assemble_parser.add_argument("--group-field", default="metadata.group_id")
    assemble_parser.add_argument("--train-fraction", type=float, default=0.6)
    assemble_parser.add_argument("--validation-fraction", type=float, default=0.2)
    assemble_parser.add_argument("--test-fraction", type=float, default=0.2)
    assemble_parser.add_argument("--seed", type=int, default=42)

    create_asset_parser = assets_subparsers.add_parser(
        "create",
        help="Create a self-contained evaluation asset workspace",
    )
    create_asset_parser.add_argument("--tenant", required=True)
    create_asset_parser.add_argument(
        "--feedback",
        required=True,
        help="Labeled JSONL using fapo-evaluation-input-v1",
    )
    create_asset_parser.add_argument(
        "--unlabeled",
        required=True,
        help="Unlabeled JSONL using fapo-evaluation-input-v1",
    )
    create_asset_parser.add_argument("--asset-id", default="v1")
    create_asset_parser.add_argument("--tenants-root", default="tenants")
    create_asset_parser.add_argument("--rubric-model", default="gpt-5.5")
    create_asset_parser.add_argument(
        "--embedding-model",
        default="text-embedding-3-small",
    )
    create_asset_parser.add_argument("--clusters", type=int, default=50)
    create_asset_parser.add_argument(
        "--match-threshold",
        type=float,
        default=0.6,
        help="Minimum Stage 5 cluster-to-trusted-intent cosine score",
    )
    create_asset_parser.add_argument(
        "--enable-synthetic-coverage",
        action="store_true",
        help="Enable optional Stage 7 synthetic case generation",
    )
    create_asset_parser.add_argument(
        "--synthetic-cases-per-cluster",
        type=int,
        default=1,
        help="Synthetic cases to request for each supported cluster",
    )

    run_asset_parser = assets_subparsers.add_parser(
        "run",
        help="Run or resume a core evaluation asset pipeline",
    )
    run_asset_parser.add_argument("--tenant", required=True)
    run_asset_parser.add_argument("--asset-id", default="v1")
    run_asset_parser.add_argument("--tenants-root", default="tenants")
    run_asset_parser.add_argument("--rubric-model")
    run_asset_parser.add_argument("--embedding-model")
    run_asset_parser.add_argument("--clusters", type=int)
    run_asset_parser.add_argument("--batch-size", type=int)
    run_asset_parser.add_argument("--match-threshold", type=float)
    run_asset_parser.add_argument("--min-trusted-examples", type=int)
    run_asset_parser.add_argument("--min-trusted-groups", type=int)
    run_asset_parser.add_argument(
        "--max-unlabeled-to-trusted-ratio",
        type=float,
    )
    run_asset_parser.add_argument(
        "--synthetic-coverage",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Enable or disable Stage 7 when resuming",
    )
    run_asset_parser.add_argument("--synthetic-cases-per-cluster", type=int)
    run_asset_parser.add_argument("--split-seed", type=int)

    extend_asset_parser = assets_subparsers.add_parser(
        "extend",
        help="Create a new asset version from additional labeled or unlabeled data",
    )
    extend_asset_parser.add_argument("--tenant", required=True)
    extend_asset_parser.add_argument("--parent-asset-id", required=True)
    extend_asset_parser.add_argument("--asset-id", required=True)
    extend_asset_parser.add_argument("--additional-feedback")
    extend_asset_parser.add_argument("--additional-unlabeled")
    extend_asset_parser.add_argument(
        "--clustering-mode",
        choices=("keep", "refresh"),
        default="keep",
    )
    extend_asset_parser.add_argument("--embedding-model")
    extend_asset_parser.add_argument("--clusters", type=int)
    extend_asset_parser.add_argument("--tenants-root", default="tenants")

    status_asset_parser = assets_subparsers.add_parser(
        "status",
        help="Read persisted evaluation asset pipeline progress",
    )
    status_asset_parser.add_argument("--tenant", required=True)
    status_asset_parser.add_argument("--asset-id", default="v1")
    status_asset_parser.add_argument("--tenants-root", default="tenants")

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

    if args.command == "ui":
        from src.hephaestus.webui import serve

        serve(Path(args.tenants_root), host=args.host, port=args.port)
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

    if args.command == "assets":
        if args.assets_command == "extend":
            import json as json_mod

            from src.hephaestus.evaluation_assets.pipeline import (
                EvaluationAssetPipeline,
            )
            from src.hephaestus.evaluation_assets.workspace import (
                EvaluationAssetLayout,
            )

            parent = EvaluationAssetLayout(
                Path(args.tenants_root),
                args.tenant,
                args.parent_asset_id,
            )
            layout = EvaluationAssetLayout(
                Path(args.tenants_root),
                args.tenant,
                args.asset_id,
            )
            updates = {
                key: value
                for key, value in {
                    "embedding_model": args.embedding_model,
                    "cluster_count": args.clusters,
                }.items()
                if value is not None
            }
            layout.initialize_extension(
                parent,
                additional_feedback=(
                    Path(args.additional_feedback)
                    if args.additional_feedback
                    else None
                ),
                additional_unlabeled=(
                    Path(args.additional_unlabeled)
                    if args.additional_unlabeled
                    else None
                ),
                clustering_mode=args.clustering_mode,
                config_updates=updates,
            )
            state = EvaluationAssetPipeline(layout).run()
            print(json_mod.dumps(state.to_dict(), indent=2, sort_keys=True))
            return

        if args.assets_command == "create":
            import json as json_mod

            from src.hephaestus.evaluation_assets.models import EvaluationAssetConfig
            from src.hephaestus.evaluation_assets.workspace import EvaluationAssetLayout

            config = EvaluationAssetConfig(
                tenant_id=args.tenant,
                asset_id=args.asset_id,
                rubric_model=args.rubric_model,
                embedding_provider=(
                    "tfidf" if args.embedding_model == "tfidf" else "openai"
                ),
                embedding_model=args.embedding_model,
                cluster_count=args.clusters,
                match_threshold=args.match_threshold,
                synthetic_coverage_enabled=args.enable_synthetic_coverage,
                synthetic_cases_per_cluster=args.synthetic_cases_per_cluster,
            )
            layout = EvaluationAssetLayout(
                Path(args.tenants_root),
                args.tenant,
                args.asset_id,
            )
            state = layout.initialize(
                config,
                Path(args.feedback),
                Path(args.unlabeled),
            )
            print(json_mod.dumps(state.to_dict(), indent=2, sort_keys=True))
            print(f"Evaluation asset workspace created at {layout.root}")
            return

        if args.assets_command == "run":
            import json as json_mod

            from src.hephaestus.evaluation_assets.pipeline import EvaluationAssetPipeline
            from src.hephaestus.evaluation_assets.workspace import EvaluationAssetLayout

            layout = EvaluationAssetLayout(
                Path(args.tenants_root),
                args.tenant,
                args.asset_id,
            )
            updates = {
                key: value
                for key, value in {
                    "rubric_model": args.rubric_model,
                    "embedding_model": args.embedding_model,
                    "cluster_count": args.clusters,
                    "batch_size": args.batch_size,
                    "match_threshold": args.match_threshold,
                    "min_trusted_examples": args.min_trusted_examples,
                    "min_trusted_groups": args.min_trusted_groups,
                    "max_unlabeled_to_trusted_ratio": (
                        args.max_unlabeled_to_trusted_ratio
                    ),
                    "synthetic_coverage_enabled": args.synthetic_coverage,
                    "synthetic_cases_per_cluster": args.synthetic_cases_per_cluster,
                    "split_seed": args.split_seed,
                }.items()
                if value is not None
            }
            if updates:
                layout.revise_config(updates)
            state = EvaluationAssetPipeline(layout).run()
            print(json_mod.dumps(state.to_dict(), indent=2, sort_keys=True))
            return

        if args.assets_command == "status":
            import json as json_mod

            from src.hephaestus.evaluation_assets.workspace import EvaluationAssetLayout

            layout = EvaluationAssetLayout(
                Path(args.tenants_root),
                args.tenant,
                args.asset_id,
            )
            print(json_mod.dumps(layout.load_state().to_dict(), indent=2, sort_keys=True))
            return

        if args.assets_command == "intent-inventory":
            from src.hephaestus.datasets.embedding_providers import OpenAIEmbeddingProvider
            from src.hephaestus.datasets.evaluation_assets import write_coverage_report, write_jsonl
            from src.hephaestus.datasets.intent_assets import (
                CoveragePolicy,
                IntentInventory,
                build_intent_inventory,
                build_intent_match_texts,
                cluster_records,
                cluster_to_dict,
                dense_vectors_to_sparse,
                load_intent_records_from_jsonl,
                load_trusted_intents_from_jsonl,
                match_clusters_to_trusted_intents,
                match_to_dict,
            )

            output_dir = Path(args.output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            records = load_intent_records_from_jsonl(
                Path(args.records),
                id_field=args.id_field,
                text_fields=args.text_field,
                route_field=args.route_field,
                group_field=args.group_field,
            )
            trusted = load_trusted_intents_from_jsonl(Path(args.trusted_intents))
            coverage_policy = CoveragePolicy(
                min_match_score=args.match_threshold,
                min_trusted_examples=args.min_trusted_examples,
                min_trusted_groups=args.min_trusted_groups,
                large_cluster_size=args.large_cluster_size,
                min_trusted_examples_for_large_cluster=args.min_trusted_examples_for_large_cluster,
                max_unlabeled_to_trusted_ratio=args.max_unlabeled_to_trusted_ratio,
            )
            if args.vectorizer == "openai":
                embedding_provider = OpenAIEmbeddingProvider(
                    model=args.embedding_model,
                    batch_size=args.embedding_batch_size,
                    timeout_seconds=args.embedding_timeout_seconds,
                    max_retries=args.embedding_max_retries,
                    retry_backoff_seconds=args.embedding_retry_backoff_seconds,
                )
                record_ids = [record.record_id for record in records]
                record_vectors = dense_vectors_to_sparse(
                    record_ids,
                    embedding_provider.embed_texts([record.text for record in records]),
                )
                clusters = cluster_records(
                    records,
                    similarity_threshold=args.similarity_threshold,
                    vectors=record_vectors,
                )
                match_texts = build_intent_match_texts(clusters, records, trusted)
                match_keys = list(match_texts)
                match_vectors = dense_vectors_to_sparse(
                    match_keys,
                    embedding_provider.embed_texts([match_texts[key] for key in match_keys]),
                )
                matches = match_clusters_to_trusted_intents(
                    clusters,
                    records,
                    trusted,
                    coverage_policy=coverage_policy,
                    vectors=match_vectors,
                )
                inventory = IntentInventory(clusters=clusters, matches=matches)
            else:
                inventory = build_intent_inventory(
                    records,
                    trusted,
                    similarity_threshold=args.similarity_threshold,
                    match_threshold=args.match_threshold,
                    coverage_policy=coverage_policy,
                )
            inventory_path = output_dir / "intent_inventory.jsonl"
            matches_path = output_dir / "intent_matches.jsonl"
            report_path = output_dir / "coverage_report.md"
            write_jsonl(inventory_path, [cluster_to_dict(item) for item in inventory.clusters])
            write_jsonl(matches_path, [match_to_dict(item) for item in inventory.matches])
            write_coverage_report(report_path, inventory.clusters, inventory.matches)
            print(
                f"Wrote {len(inventory.clusters)} clusters and "
                f"{len(inventory.matches)} matches to {output_dir}"
            )
            return

        if args.assets_command == "assemble":
            from src.hephaestus.datasets.evaluation_assets import (
                assemble_dataset_bundle,
                filter_synthetic_cases,
                load_fapo_cases,
                sha256_file,
                synthetic_issue_to_dict,
                write_jsonl,
            )

            trusted_path = Path(args.trusted_cases)
            synthetic_path = Path(args.synthetic_cases)
            regression_path = Path(args.regression_cases) if args.regression_cases else None
            triage_path = Path(args.triage_cases) if args.triage_cases else None

            trusted_cases = load_fapo_cases(trusted_path)
            synthetic_candidates = load_fapo_cases(synthetic_path)
            regression_cases = load_fapo_cases(regression_path) if regression_path else []
            triage_cases = load_fapo_cases(triage_path) if triage_path else []
            filtered = filter_synthetic_cases(
                synthetic_candidates,
                existing_cases=trusted_cases,
            )
            source_hashes = {
                "trusted_cases": sha256_file(trusted_path),
                "synthetic_cases": sha256_file(synthetic_path),
            }
            if regression_path:
                source_hashes["regression_cases"] = sha256_file(regression_path)
            if triage_path:
                source_hashes["triage_cases"] = sha256_file(triage_path)

            manifest = assemble_dataset_bundle(
                output_dir=Path(args.output_dir),
                dataset_version=args.dataset_version,
                trusted_cases=trusted_cases,
                synthetic_cases=filtered.accepted,
                regression_cases=regression_cases,
                triage_cases=triage_cases,
                group_path=args.group_field,
                train_fraction=args.train_fraction,
                validation_fraction=args.validation_fraction,
                test_fraction=args.test_fraction,
                seed=args.seed,
                source_hashes=source_hashes,
            )
            output_dir = Path(args.output_dir)
            write_jsonl(output_dir / "rejected_synthetic.jsonl", filtered.rejected)
            write_jsonl(
                output_dir / "synthetic_filter_issues.jsonl",
                [synthetic_issue_to_dict(issue) for issue in filtered.issues],
            )
            rejected_count = len(filtered.rejected)
            print(
                f"Wrote dataset bundle {manifest.dataset_version} to {args.output_dir}; "
                f"accepted synthetic={len(filtered.accepted)} rejected synthetic={rejected_count}"
            )
            return

        raise ValueError(f"Unsupported assets command: {args.assets_command}")

    raise ValueError(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    main()
