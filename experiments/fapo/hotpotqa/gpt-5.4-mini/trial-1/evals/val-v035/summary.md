# Evaluation Summary

Total cases: 300

## Composite Score
- average: 71.00

## Score Breakdown
- exact_match: 71.00
- f1: 77.37

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 1.295 | 0.915 | 1.700 |
| summarize_hop1 | 1.351 | 1.262 | 2.000 |
| query_hop2 | 1.115 | 1.050 | 1.550 |
| retrieve_hop2 | 1.288 | 1.320 | 1.616 |
| summarize_hop2 | 1.610 | 1.512 | 2.431 |
| answer | 0.778 | 0.718 | 1.265 |
| **Total** | **7.436** | **6.974** | **9.447** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 86 |
| query_hop2 | 1 |
