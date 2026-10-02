# Evaluation Summary

Total cases: 300

## Composite Score
- average: 65.67

## Score Breakdown
- exact_match: 65.67
- f1: 73.18

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.004 | 0.002 | 0.006 |
| summarize_hop1 | 2.679 | 2.583 | 4.260 |
| query_hop2 | 1.393 | 1.235 | 2.060 |
| retrieve_hop2 | 1.095 | 1.297 | 1.603 |
| summarize_hop2 | 2.359 | 2.179 | 3.760 |
| answer | 1.718 | 1.477 | 2.418 |
| **Total** | **9.248** | **8.735** | **13.533** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 103 |
