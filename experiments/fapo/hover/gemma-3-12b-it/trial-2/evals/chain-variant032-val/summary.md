# Evaluation Summary

Total cases: 300

## Composite Score
- average: 76.67

## Score Breakdown
- num_found: 2.74
- num_gold: 3.00
- num_missing: 0.26
- partial_recall: 91.33
- recall: 76.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.005 | 0.004 | 0.006 |
| summarize_hop1 | 3.184 | 2.523 | 6.718 |
| query_hop2 | 0.368 | 0.315 | 0.624 |
| retrieve_hop2 | 0.339 | 0.005 | 1.505 |
| summarize_hop2 | 6.821 | 5.788 | 10.356 |
| query_hop3 | 0.361 | 0.324 | 0.475 |
| retrieve_hop3 | 0.764 | 1.055 | 1.566 |
| summarize_hop3 | 6.978 | 6.326 | 12.814 |
| query_hop4 | 0.503 | 0.418 | 0.926 |
| retrieve_hop4 | 1.441 | 1.303 | 1.642 |
| query_hop5 | 0.517 | 0.480 | 0.759 |
| retrieve_hop5 | 2.561 | 2.556 | 3.156 |
| combine_retrievals | 0.000 | 0.000 | 0.001 |
| **Total** | **23.842** | **22.315** | **33.133** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop5 | 70 |
