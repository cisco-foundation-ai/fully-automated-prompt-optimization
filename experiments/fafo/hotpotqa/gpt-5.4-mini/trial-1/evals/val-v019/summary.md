# Evaluation Summary

Total cases: 300

## Composite Score
- average: 69.00

## Score Breakdown
- exact_match: 69.00
- f1: 76.89

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.104 | 0.002 | 0.115 |
| summarize_hop1 | 1.403 | 1.295 | 2.100 |
| query_hop2 | 1.103 | 1.043 | 1.484 |
| retrieve_hop2 | 0.508 | 0.002 | 1.675 |
| summarize_hop2 | 1.587 | 1.486 | 2.343 |
| answer | 0.965 | 0.910 | 1.431 |
| **Total** | **5.671** | **5.101** | **8.293** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 92 |
| query_hop2 | 1 |
