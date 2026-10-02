# Evaluation Summary

Total cases: 300

## Composite Score
- average: 60.33

## Score Breakdown
- exact_match: 60.33
- f1: 69.37

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.046 | 0.002 | 0.015 |
| summarize_hop1 | 2.625 | 2.361 | 4.604 |
| query_hop2 | 1.104 | 1.016 | 1.910 |
| retrieve_hop2 | 0.393 | 0.002 | 1.491 |
| summarize_hop2 | 2.777 | 2.468 | 5.183 |
| answer | 1.130 | 1.000 | 2.016 |
| **Total** | **8.074** | **7.614** | **12.433** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 119 |
