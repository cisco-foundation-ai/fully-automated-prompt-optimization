# Evaluation Summary

Total cases: 300

## Composite Score
- average: 69.67

## Score Breakdown
- exact_match: 69.67
- f1: 78.19

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.028 | 0.002 | 0.010 |
| summarize_hop1 | 2.367 | 2.157 | 3.456 |
| query_hop2 | 1.337 | 1.122 | 1.956 |
| retrieve_hop2 | 0.338 | 0.002 | 1.616 |
| summarize_hop2 | 1.795 | 1.520 | 2.624 |
| answer | 0.980 | 0.804 | 1.610 |
| **Total** | **6.844** | **6.021** | **10.344** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 91 |
