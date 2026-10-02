# Evaluation Summary

Total cases: 300

## Composite Score
- average: 72.00

## Score Breakdown
- exact_match: 72.00
- f1: 79.04

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.039 | 0.002 | 0.009 |
| summarize_hop1 | 1.266 | 1.191 | 1.817 |
| query_hop2 | 1.076 | 1.020 | 1.516 |
| retrieve_hop2 | 0.268 | 0.002 | 1.533 |
| summarize_hop2 | 1.274 | 1.224 | 1.685 |
| answer | 0.957 | 0.899 | 1.382 |
| **Total** | **4.879** | **4.606** | **6.712** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 84 |
