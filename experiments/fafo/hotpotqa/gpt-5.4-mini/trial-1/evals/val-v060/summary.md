# Evaluation Summary

Total cases: 300

## Composite Score
- average: 70.33

## Score Breakdown
- exact_match: 70.33
- f1: 77.22

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.154 | 0.002 | 0.123 |
| summarize_hop1 | 1.392 | 1.303 | 2.117 |
| query_hop2 | 1.202 | 1.090 | 1.714 |
| retrieve_hop2 | 0.401 | 0.002 | 1.604 |
| summarize_hop2 | 1.654 | 1.534 | 2.534 |
| answer | 0.966 | 0.753 | 1.345 |
| **Total** | **5.769** | **5.050** | **8.788** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 89 |
