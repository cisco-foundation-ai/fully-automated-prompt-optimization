# Evaluation Summary

Total cases: 300

## Composite Score
- average: 24.67

## Score Breakdown
- num_found: 1.86
- num_gold: 3.00
- num_missing: 1.14
- partial_recall: 62.00
- recall: 24.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.003 | 0.002 | 0.005 |
| summarize_hop1 | 1.798 | 1.518 | 2.592 |
| query_hop2 | 0.925 | 0.748 | 1.297 |
| retrieve_hop2 | 1.254 | 1.139 | 1.629 |
| summarize_hop2 | 1.998 | 1.837 | 2.659 |
| query_hop3 | 0.872 | 0.740 | 1.164 |
| retrieve_hop3 | 1.032 | 1.081 | 1.616 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **7.883** | **7.194** | **13.426** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 226 |
