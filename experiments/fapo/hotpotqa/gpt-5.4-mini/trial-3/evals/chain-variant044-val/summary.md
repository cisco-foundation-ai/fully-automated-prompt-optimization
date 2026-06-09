# Evaluation Summary

Total cases: 300

## Composite Score
- average: 72.67

## Score Breakdown
- exact_match: 72.67
- f1: 79.04

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.048 | 0.002 | 0.008 |
| summarize_hop1 | 1.647 | 1.324 | 2.631 |
| query_hop2 | 1.276 | 1.061 | 2.054 |
| retrieve_hop2 | 0.287 | 0.002 | 1.176 |
| summarize_hop2 | 1.531 | 1.342 | 2.665 |
| answer | 1.097 | 0.952 | 1.807 |
| **Total** | **5.886** | **5.105** | **9.193** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 82 |
