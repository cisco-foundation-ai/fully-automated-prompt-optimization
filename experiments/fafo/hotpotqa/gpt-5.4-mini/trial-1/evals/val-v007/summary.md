# Evaluation Summary

Total cases: 300

## Composite Score
- average: 65.00

## Score Breakdown
- exact_match: 65.00
- f1: 72.79

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.098 | 0.002 | 0.110 |
| summarize_hop1 | 1.124 | 1.044 | 1.661 |
| query_hop2 | 1.125 | 1.042 | 1.865 |
| retrieve_hop2 | 0.674 | 0.003 | 1.620 |
| summarize_hop2 | 1.109 | 1.019 | 1.827 |
| answer | 0.995 | 0.889 | 1.484 |
| **Total** | **5.126** | **4.592** | **8.009** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 104 |
| query_hop2 | 1 |
