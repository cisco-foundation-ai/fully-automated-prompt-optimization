# Evaluation Summary

Total cases: 300

## Composite Score
- average: 36.67

## Score Breakdown
- num_found: 2.15
- num_gold: 3.00
- num_missing: 0.85
- partial_recall: 71.78
- recall: 36.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.970 | 0.536 | 1.723 |
| summarize_hop1 | 1.854 | 1.680 | 2.662 |
| query_hop2 | 0.907 | 0.685 | 1.158 |
| retrieve_hop2 | 1.307 | 1.353 | 1.645 |
| summarize_hop2 | 2.265 | 2.010 | 3.395 |
| query_hop3 | 0.940 | 0.686 | 1.128 |
| retrieve_hop3 | 1.282 | 1.109 | 1.648 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **9.525** | **8.782** | **18.502** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 190 |
