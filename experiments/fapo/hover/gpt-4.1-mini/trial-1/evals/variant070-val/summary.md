# Evaluation Summary

Total cases: 300

## Composite Score
- average: 52.67

## Score Breakdown
- num_found: 2.40
- num_gold: 3.00
- partial_recall: 80.11
- recall: 52.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.611 | 0.154 | 1.659 |
| summarize_hop1 | 6.235 | 3.673 | 17.427 |
| query_hop2 | 1.151 | 0.761 | 1.745 |
| retrieve_hop2 | 2.904 | 1.714 | 8.355 |
| summarize_hop2 | 5.330 | 3.872 | 12.858 |
| query_hop3 | 1.409 | 0.871 | 2.539 |
| retrieve_hop3 | 7.163 | 7.446 | 13.537 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **24.802** | **22.340** | **44.214** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 142 |
