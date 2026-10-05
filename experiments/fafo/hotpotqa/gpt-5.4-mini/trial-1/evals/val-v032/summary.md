# Evaluation Summary

Total cases: 300

## Composite Score
- average: 64.33

## Score Breakdown
- exact_match: 64.33
- f1: 73.14

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.140 | 0.002 | 0.119 |
| summarize_hop1 | 1.355 | 1.255 | 1.879 |
| query_hop2 | 1.044 | 1.022 | 1.350 |
| retrieve_hop2 | 0.365 | 0.002 | 1.576 |
| summarize_hop2 | 1.576 | 1.467 | 2.368 |
| answer | 0.821 | 0.773 | 1.194 |
| **Total** | **5.302** | **4.796** | **8.337** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 107 |
