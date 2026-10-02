# Evaluation Summary

Total cases: 300

## Composite Score
- average: 68.33

## Score Breakdown
- num_found: 2.64
- num_gold: 3.00
- partial_recall: 88.11
- recall: 68.33

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.003 | 0.002 | 0.003 |
| summarize_hop1 | 2.326 | 2.155 | 3.557 |
| query_hop2 | 0.812 | 0.746 | 1.174 |
| retrieve_hop2 | 1.244 | 1.475 | 1.658 |
| summarize_hop2 | 1.524 | 1.409 | 2.090 |
| query_hop3 | 0.939 | 0.611 | 1.025 |
| retrieve_hop3 | 0.622 | 0.003 | 1.606 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **7.470** | **6.892** | **10.166** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 95 |
