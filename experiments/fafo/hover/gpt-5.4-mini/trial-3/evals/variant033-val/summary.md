# Evaluation Summary

Total cases: 300

## Composite Score
- average: 36.67

## Score Breakdown
- num_found: 2.17
- num_gold: 3.00
- num_missing: 0.83
- partial_recall: 72.33
- recall: 36.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.003 | 0.002 | 0.004 |
| summarize_hop1 | 1.775 | 1.703 | 2.716 |
| query_hop2 | 0.746 | 0.681 | 1.129 |
| retrieve_hop2 | 1.336 | 1.331 | 1.663 |
| summarize_hop2 | 2.292 | 1.998 | 3.285 |
| query_hop3 | 0.799 | 0.690 | 1.038 |
| retrieve_hop3 | 1.358 | 1.345 | 1.664 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **8.309** | **7.819** | **10.929** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 190 |
