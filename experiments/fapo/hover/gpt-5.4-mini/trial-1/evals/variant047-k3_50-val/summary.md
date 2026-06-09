# Evaluation Summary

Total cases: 300

## Composite Score
- average: 77.67

## Score Breakdown
- num_found: 2.74
- num_gold: 3.00
- partial_recall: 91.33
- recall: 77.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.004 | 0.002 | 0.005 |
| summarize_hop1 | 2.536 | 2.276 | 4.293 |
| query_hop2 | 0.911 | 0.730 | 1.337 |
| retrieve_hop2 | 0.680 | 0.002 | 1.685 |
| summarize_hop2 | 3.724 | 3.370 | 6.505 |
| query_hop3 | 0.885 | 0.742 | 1.712 |
| retrieve_hop3 | 1.038 | 1.524 | 1.665 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **9.778** | **9.212** | **15.168** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 67 |
