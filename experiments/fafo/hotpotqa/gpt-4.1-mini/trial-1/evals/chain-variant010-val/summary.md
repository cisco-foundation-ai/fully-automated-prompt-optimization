# Evaluation Summary

Total cases: 300

## Composite Score
- average: 68.67

## Score Breakdown
- exact_match: 68.67
- f1: 76.74

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.014 | 0.002 | 0.008 |
| summarize_hop1 | 2.901 | 2.468 | 5.249 |
| query_hop2 | 1.575 | 1.372 | 2.821 |
| retrieve_hop2 | 1.146 | 1.323 | 1.656 |
| summarize_hop2 | 2.570 | 2.308 | 4.662 |
| answer | 1.437 | 1.325 | 2.227 |
| **Total** | **9.643** | **8.922** | **15.276** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 94 |
