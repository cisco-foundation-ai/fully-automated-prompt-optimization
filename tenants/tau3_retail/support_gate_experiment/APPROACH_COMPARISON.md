# Guideline-matching approach comparison

## Comparable sampled accuracy

The table below uses the same 30 task-disjoint development episodes, the same
13-guideline library, and the same frozen Codex model-expert applicability
labels. There are 59 labeled applicable episode-guideline attachments.

For the similarity-only row, a guideline is attached when it appears in the
union of the stored cluster-similarity and episode-similarity retrieval sets.
This row was calculated from the already persisted candidate rows; no model was
rerun. The other three rows reuse their recorded audit results.

| Approach | TP / FP / FN | Precision | Recall | F1 | Exact episode set |
|---|---:|---:|---:|---:|---:|
| 1. Similarity union only | 53 / 163 / 6 | 24.54% | 89.83% | 38.55% | 0.00% |
| 2. Deterministic applicability contracts | 52 / 15 / 7 | 77.61% | 88.14% | 82.54% | **60.00%** |
| 3. GPT-5.6 Luna generic v2 | 54 / 16 / 5 | 77.14% | 91.53% | 83.72% | 46.67% |
| 4. Full GPT-5.5 episode gate | **55 / 13 / 4** | **80.88%** | **93.22%** | **86.61%** | 53.33% |

The similarity union averaged 7.2 candidates per sampled episode, with a range
of 6–9. Across all 331 stored episodes it averaged 7.18 candidates, with a
range of 6–10. Its purpose is therefore candidate retrieval, not final
applicability: it retained most applicable guidelines but also attached many
irrelevant ones.

The historical cluster-top-1 similarity method shows the opposite tradeoff. On
the earlier 62-case audit it achieved 74.2% precision but only 21.6% recall and
4.8% exact-set accuracy. That result used a different 14-guideline library, so
it is not included as a fifth row in the controlled table.

## Processing time and model usage

The timing records were produced by different runs and are not a controlled
latency benchmark. The 328-episode equivalent makes their scale easier to
compare. Common guideline creation and intent clustering are excluded. The
similarity matching stage took 5.722 seconds for 331 episodes and is included
in the end-to-end equivalents for rows 2–4.

| Approach | Recorded processing | Semantic-model usage | Approximate 328-episode selection time |
|---|---|---|---:|
| 1. Similarity union only | 5.722 s for 331 episodes | 0 rubric-LLM calls | **5.7 s** |
| 2. Deterministic applicability contracts | 8.869 s for the 328-episode Stage 6/7 gate | 0 rubric-LLM calls, 0 tokens | **14.6 s**, including similarity matching |
| 3. GPT-5.6 Luna generic v2 | 126.021 s for 30 episodes | 10 calls, 177,922 tokens, `$0.046520` | **about 23m 04s**, linearly extrapolated and including matching |
| 4. Full GPT-5.5 episode gate | 71m 13s for 328 episodes | 66 calls, 1,777,510 tokens | **about 71m 19s**, including matching |

The Luna full-size estimate is approximately 110 calls, 1.95 million tokens,
and `$0.509` if its measured three-episode batching and per-episode usage scale
linearly. The recorded Luna audit gave all 13 guidelines to every episode. The
proposed similarity-union-plus-Luna path would provide about 7.18 candidates on
average, so its token usage may be lower; that exact combined path has not yet
been run.

## Interpretation

- Similarity alone is fast and useful for high-recall retrieval, but it cannot
  be used as the final guideline labeler. In this sample it generated 163 false
  attachments and no exact episode-level matches.
- Deterministic contracts are almost free and achieved the highest exact-set
  rate, but they require domain-specific contract authoring and did not beat
  the language models on attachment F1.
- Luna recovered most of GPT-5.5's sampled accuracy at substantially lower
  measured latency and price. Its generic-v2 F1 was 2.89 points below GPT-5.5.
- GPT-5.5 was the most accurate recorded semantic gate, but also the slowest.

One retrieval issue must be fixed before freezing the proposed architecture:
the current similarity union missed 6 of the 59 reference attachments, so a
Luna gate restricted to that union has a maximum possible sampled recall of
89.83%. Candidate retrieval should be tuned for higher recall before measuring
the exact union-plus-Luna configuration.

The selected simple tuning changes the bounded policy from top-6/top-6 to
top-9/top-9 with a cap of 10. In replay it retained 58 of 59 requirements
(98.31%) with 9.53 candidates per episode. Routes with 20 or fewer guidelines
remain exhaustive; Tau Retail has 13, so its actual candidate recall is 100%.
See `retrieval_tuning_v1.json`.

The combined method is now implemented in
`scripts/run_latest_luna_pipeline.py`. It preserves the GPT-5.5 guideline
library, consumes the Stage 5 cluster-plus-episode candidate rows, asks Luna to
review every candidate directly, and derives cluster support only after the
episode decisions. A preparation-only validation found 331 eligible episodes,
13 candidates per episode under Tau Retail's small-route exhaustive rule, and
67 bounded Luna batches. No full Luna run has been launched yet.

These labels are sealed Codex model-expert annotations, not human ground truth,
and several factual-guideline disagreements may be annotation omissions. The
numbers are development diagnostics until a human adjudicates the sample.

## Reused sources

- Similarity candidates and timing:
  `baseline-gpt55-episode-v1/stages/05_coverage_decisions/episode_guideline_candidates.jsonl`
  and `baseline-gpt55-episode-v1/pipeline_state.json`
- Deterministic and GPT-5.5 sampled scores:
  `held_out_audit_v1/scoring/held_out_score.json`
- Derived similarity-union sampled score:
  `held_out_audit_v1/scoring/similarity_union_score.json`
- Deterministic live timing:
  `live_deterministic_only_run_v3/run_result.json`
- Luna score, timing, calls, tokens, and cost:
  `held_out_audit_v1/model_selector_gpt56_luna_generic_v2/run_result.json`
- Full GPT-5.5 timing and usage: `RESULTS_GPT55_EPISODE_GATE.md`
- Historical cluster-top-1 audit: `RESULTS_CODEX_AUDIT.md`
