# Evaluation Summary

Total cases: 300

## Composite Score
- average: 67.33

## Score Breakdown
- exact_match: 67.33
- f1: 76.29

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.036 | 0.002 | 0.011 |
| summarize_hop1 | 1.492 | 1.323 | 2.519 |
| query_hop2 | 1.338 | 1.043 | 2.473 |
| retrieve_hop2 | 0.310 | 0.002 | 1.492 |
| summarize_hop2 | 1.671 | 1.365 | 2.717 |
| answer | 1.618 | 1.060 | 2.808 |
| **Total** | **6.465** | **5.390** | **12.155** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 97 |
| query_hop2 | 1 |
