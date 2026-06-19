# Evaluation Summary

Total cases: 300

## Composite Score
- average: 71.00

## Score Breakdown
- exact_match: 71.00
- f1: 76.90

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.025 | 0.003 | 0.013 |
| summarize_hop1 | 1.442 | 1.288 | 2.492 |
| query_hop2 | 1.218 | 1.042 | 2.454 |
| retrieve_hop2 | 0.286 | 0.002 | 1.590 |
| summarize_hop2 | 1.484 | 1.300 | 2.458 |
| answer | 1.147 | 0.987 | 1.822 |
| **Total** | **5.600** | **4.978** | **8.343** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 87 |
