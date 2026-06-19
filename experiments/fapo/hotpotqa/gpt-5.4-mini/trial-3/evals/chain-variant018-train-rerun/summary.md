# Evaluation Summary

Total cases: 150

## Composite Score
- average: 74.00

## Score Breakdown
- exact_match: 74.00
- f1: 81.28

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.097 | 0.002 | 0.042 |
| summarize_hop1 | 1.301 | 1.160 | 1.841 |
| query_hop2 | 1.066 | 0.940 | 1.844 |
| retrieve_hop2 | 0.587 | 0.002 | 1.624 |
| summarize_hop2 | 1.319 | 1.155 | 1.796 |
| answer | 1.045 | 0.843 | 1.480 |
| **Total** | **5.414** | **4.507** | **8.785** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 39 |
