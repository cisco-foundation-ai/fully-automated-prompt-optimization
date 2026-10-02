# Evaluation Summary

Total cases: 300

## Composite Score
- average: 68.33

## Score Breakdown
- num_found: 2.60
- num_gold: 3.00
- partial_recall: 86.78
- recall: 68.33

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 1.339 | 1.404 | 3.219 |
| summarize_hop1 | 4.932 | 3.609 | 12.249 |
| query_hop2 | 0.959 | 0.755 | 1.296 |
| retrieve_hop2 | 2.176 | 1.610 | 5.291 |
| summarize_hop2 | 5.171 | 3.962 | 10.805 |
| query_hop3 | 1.008 | 0.873 | 1.693 |
| retrieve_hop3 | 6.640 | 5.511 | 15.586 |
| retrieve_mining | 0.429 | 0.026 | 3.094 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **22.655** | **20.669** | **39.532** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_mining | 95 |
