# Evaluation Summary

Total cases: 300

## Composite Score
- average: 98.33

## Score Breakdown
- num_found: 2.98
- num_gold: 3.00
- partial_recall: 99.44
- recall: 98.33

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.926 | 0.466 | 1.631 |
| summarize_hop1 | 31.630 | 26.053 | 64.615 |
| query_hop2 | 1.872 | 1.111 | 5.327 |
| retrieve_hop2 | 9.502 | 8.742 | 12.185 |
| summarize_hop2 | 34.590 | 26.441 | 69.423 |
| query_hop3 | 1.295 | 1.026 | 1.922 |
| retrieve_hop3 | 8.152 | 8.327 | 11.822 |
| summarize_hop3 | 31.861 | 26.537 | 53.625 |
| query_hop4 | 1.964 | 1.739 | 3.213 |
| retrieve_hop4 | 14.435 | 13.587 | 18.339 |
| summarize_hop4 | 78.713 | 74.436 | 127.725 |
| query_hop5 | 4.659 | 3.206 | 12.743 |
| retrieve_hop5 | 24.352 | 24.454 | 30.552 |
| combine_retrievals | 0.016 | 0.015 | 0.032 |
| **Total** | **243.968** | **235.137** | **344.789** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop5 | 5 |
