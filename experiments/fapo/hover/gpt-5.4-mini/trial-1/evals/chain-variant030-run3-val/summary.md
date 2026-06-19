# Evaluation Summary

Total cases: 300

## Composite Score
- average: 76.33

## Score Breakdown
- num_found: 2.73
- num_gold: 3.00
- partial_recall: 91.00
- recall: 76.33

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.021 | 0.002 | 0.009 |
| summarize_hop1 | 2.278 | 2.114 | 3.446 |
| query_hop2 | 0.731 | 0.674 | 1.006 |
| retrieve_hop2 | 0.712 | 0.002 | 1.696 |
| summarize_hop2 | 3.281 | 2.915 | 5.042 |
| query_hop3 | 0.871 | 0.704 | 1.339 |
| retrieve_hop3 | 0.628 | 0.002 | 1.671 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **8.522** | **8.015** | **13.134** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 71 |
