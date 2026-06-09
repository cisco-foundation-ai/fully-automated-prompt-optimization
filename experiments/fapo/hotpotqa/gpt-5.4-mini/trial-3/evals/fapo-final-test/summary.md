# Evaluation Summary

Total cases: 300

## Composite Score
- average: 71.00

## Score Breakdown
- exact_match: 71.00
- f1: 78.78

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 1.088 | 1.284 | 1.680 |
| summarize_hop1 | 1.411 | 1.215 | 2.116 |
| query_hop2 | 1.121 | 1.038 | 1.557 |
| retrieve_hop2 | 1.332 | 1.368 | 1.633 |
| summarize_hop2 | 1.418 | 1.236 | 2.182 |
| answer | 1.026 | 0.918 | 1.487 |
| **Total** | **7.396** | **6.982** | **10.971** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 87 |
