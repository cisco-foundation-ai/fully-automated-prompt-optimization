# Evaluation Summary

Total cases: 300

## Composite Score
- average: 66.00

## Score Breakdown
- exact_match: 66.00
- f1: 73.75

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.138 | 0.002 | 0.110 |
| summarize_hop1 | 1.181 | 1.113 | 1.730 |
| query_hop2 | 1.130 | 1.035 | 1.720 |
| retrieve_hop2 | 0.420 | 0.002 | 1.580 |
| summarize_hop2 | 1.524 | 1.461 | 2.199 |
| answer | 0.812 | 0.762 | 1.160 |
| **Total** | **5.205** | **4.700** | **8.198** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 102 |
