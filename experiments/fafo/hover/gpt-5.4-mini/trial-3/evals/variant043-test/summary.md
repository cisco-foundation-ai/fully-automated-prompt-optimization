# Evaluation Summary

Total cases: 300

## Composite Score
- average: 60.67

## Score Breakdown
- num_found: 2.52
- num_gold: 3.00
- num_missing: 0.48
- partial_recall: 84.11
- recall: 60.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 1.134 | 1.324 | 1.706 |
| summarize_hop1 | 2.975 | 2.540 | 5.487 |
| query_hop2 | 0.842 | 0.746 | 1.182 |
| retrieve_hop2 | 1.392 | 1.495 | 1.634 |
| summarize_hop2 | 3.278 | 2.869 | 6.000 |
| query_hop3 | 0.771 | 0.718 | 1.092 |
| retrieve_hop3 | 1.407 | 1.486 | 1.651 |
| combine_retrievals | 0.000 | 0.000 | 0.001 |
| **Total** | **11.800** | **11.229** | **17.205** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 118 |
