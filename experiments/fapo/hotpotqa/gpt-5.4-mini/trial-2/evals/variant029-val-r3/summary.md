# Evaluation Summary

Total cases: 300

## Composite Score
- average: 69.67

## Score Breakdown
- exact_match: 69.67
- f1: 76.44

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.048 | 0.003 | 0.014 |
| summarize_hop1 | 2.496 | 2.165 | 3.323 |
| query_hop2 | 1.339 | 1.167 | 1.988 |
| retrieve_hop2 | 0.295 | 0.002 | 1.479 |
| summarize_hop2 | 1.730 | 1.603 | 2.584 |
| answer | 1.072 | 0.888 | 1.574 |
| **Total** | **6.978** | **6.321** | **10.401** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 91 |
