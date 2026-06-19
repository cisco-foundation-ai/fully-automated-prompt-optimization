# Evaluation Summary

Total cases: 300

## Composite Score
- average: 68.00

## Score Breakdown
- exact_match: 68.00
- f1: 75.42

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.046 | 0.002 | 0.011 |
| summarize_hop1 | 1.237 | 1.181 | 1.711 |
| query_hop2 | 1.012 | 0.974 | 1.437 |
| retrieve_hop2 | 0.496 | 0.002 | 1.596 |
| summarize_hop2 | 1.247 | 1.206 | 1.648 |
| answer | 0.990 | 0.919 | 1.418 |
| **Total** | **5.027** | **4.625** | **6.700** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 96 |
