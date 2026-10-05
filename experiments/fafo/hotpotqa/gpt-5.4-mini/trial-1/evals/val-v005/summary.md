# Evaluation Summary

Total cases: 300

## Composite Score
- average: 64.33

## Score Breakdown
- exact_match: 64.33
- f1: 71.15

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.177 | 0.002 | 0.129 |
| summarize_hop1 | 1.183 | 1.109 | 1.765 |
| query_hop2 | 1.001 | 0.929 | 1.557 |
| retrieve_hop2 | 0.445 | 0.002 | 1.656 |
| summarize_hop2 | 1.124 | 1.072 | 1.634 |
| answer | 1.001 | 0.767 | 1.211 |
| **Total** | **4.931** | **4.210** | **6.927** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 107 |
