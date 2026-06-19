# Evaluation Summary

Total cases: 300

## Composite Score
- average: 55.00

## Score Breakdown
- num_found: 2.49
- num_gold: 3.00
- num_missing: 0.51
- partial_recall: 82.89
- recall: 55.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.007 | 0.002 | 0.014 |
| summarize_hop1 | 3.154 | 2.646 | 5.521 |
| query_hop2 | 0.775 | 0.694 | 1.042 |
| retrieve_hop2 | 1.209 | 1.466 | 1.657 |
| summarize_hop2 | 3.503 | 3.067 | 6.120 |
| query_hop3 | 0.817 | 0.722 | 1.201 |
| retrieve_hop3 | 1.391 | 1.531 | 1.659 |
| combine_retrievals | 0.000 | 0.000 | 0.001 |
| **Total** | **10.857** | **10.452** | **15.700** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 135 |
