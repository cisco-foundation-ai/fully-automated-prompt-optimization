# Evaluation Summary

Total cases: 150

## Composite Score
- average: 72.00

## Score Breakdown
- exact_match: 72.00
- f1: 78.52

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.006 | 0.002 | 0.007 |
| summarize_hop1 | 1.642 | 1.567 | 2.920 |
| query_hop2 | 1.158 | 1.085 | 1.762 |
| retrieve_hop2 | 1.057 | 0.100 | 1.693 |
| summarize_hop2 | 1.719 | 1.587 | 2.723 |
| answer | 0.958 | 0.899 | 1.285 |
| **Total** | **6.540** | **6.127** | **9.337** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 42 |
