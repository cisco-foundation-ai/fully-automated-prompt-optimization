# Evaluation Summary

Total cases: 300

## Composite Score
- average: 99.00

## Score Breakdown
- num_found: 2.99
- num_gold: 3.00
- partial_recall: 99.67
- recall: 99.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 1.026 | 0.552 | 1.705 |
| summarize_hop1 | 29.837 | 25.770 | 55.163 |
| query_hop2 | 1.511 | 1.063 | 3.706 |
| retrieve_hop2 | 10.884 | 10.950 | 12.914 |
| summarize_hop2 | 33.727 | 27.337 | 64.308 |
| query_hop3 | 1.372 | 1.069 | 1.744 |
| retrieve_hop3 | 9.303 | 9.508 | 12.502 |
| summarize_hop3 | 30.271 | 25.622 | 53.519 |
| query_hop4 | 1.952 | 1.742 | 3.033 |
| retrieve_hop4 | 11.090 | 11.162 | 15.868 |
| summarize_hop4 | 36.722 | 33.967 | 60.047 |
| query_hop5 | 3.252 | 2.287 | 9.304 |
| retrieve_hop5 | 19.728 | 19.494 | 26.101 |
| combine_retrievals | 0.011 | 0.010 | 0.022 |
| **Total** | **190.687** | **181.283** | **272.025** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop5 | 3 |
