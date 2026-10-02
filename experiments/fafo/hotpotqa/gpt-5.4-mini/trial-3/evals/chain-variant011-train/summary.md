# Evaluation Summary

Total cases: 150

## Composite Score
- average: 74.00

## Score Breakdown
- exact_match: 74.00
- f1: 80.52

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.057 | 0.002 | 0.040 |
| summarize_hop1 | 1.564 | 1.471 | 2.108 |
| query_hop2 | 1.123 | 0.964 | 1.706 |
| retrieve_hop2 | 0.748 | 0.002 | 1.675 |
| summarize_hop2 | 1.323 | 1.189 | 1.972 |
| answer | 0.792 | 0.742 | 1.088 |
| **Total** | **5.608** | **4.774** | **8.597** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 39 |
