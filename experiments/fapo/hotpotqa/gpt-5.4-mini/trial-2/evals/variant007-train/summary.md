# Evaluation Summary

Total cases: 150

## Composite Score
- average: 70.67

## Score Breakdown
- exact_match: 70.67
- f1: 77.99

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.056 | 0.002 | 0.069 |
| summarize_hop1 | 1.648 | 1.546 | 2.420 |
| query_hop2 | 1.191 | 1.087 | 1.820 |
| retrieve_hop2 | 0.725 | 0.002 | 1.640 |
| summarize_hop2 | 1.672 | 1.550 | 2.566 |
| answer | 0.898 | 0.792 | 1.469 |
| **Total** | **6.190** | **5.456** | **9.068** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 44 |
