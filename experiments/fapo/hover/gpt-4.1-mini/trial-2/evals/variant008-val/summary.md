# Evaluation Summary

Total cases: 300

## Composite Score
- average: 19.00

## Score Breakdown
- num_found: 1.78
- num_gold: 3.00
- partial_recall: 59.22
- recall: 19.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.019 | 0.002 | 0.009 |
| summarize_hop1 | 2.838 | 2.142 | 6.309 |
| query_hop2 | 0.831 | 0.529 | 1.331 |
| retrieve_hop2 | 0.511 | 0.002 | 1.616 |
| summarize_hop2 | 3.783 | 2.691 | 7.691 |
| query_hop3 | 0.812 | 0.535 | 1.392 |
| retrieve_hop3 | 0.340 | 0.002 | 1.544 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **9.133** | **7.362** | **16.434** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 243 |
