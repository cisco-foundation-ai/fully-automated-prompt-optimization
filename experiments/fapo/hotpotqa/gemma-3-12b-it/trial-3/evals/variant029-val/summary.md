# Evaluation Summary

Total cases: 300

## Composite Score
- average: 60.67

## Score Breakdown
- exact_match: 60.67
- f1: 69.25

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.028 | 0.002 | 0.010 |
| summarize_hop1 | 2.125 | 2.003 | 3.572 |
| query_hop2 | 1.064 | 1.035 | 1.416 |
| retrieve_hop2 | 0.807 | 0.010 | 1.636 |
| summarize_hop2 | 3.832 | 3.692 | 6.639 |
| answer | 1.134 | 1.069 | 1.684 |
| **Total** | **8.990** | **8.682** | **12.913** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 118 |
