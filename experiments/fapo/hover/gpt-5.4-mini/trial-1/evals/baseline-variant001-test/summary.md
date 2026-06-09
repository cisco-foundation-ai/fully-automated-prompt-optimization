# Evaluation Summary

Total cases: 300

## Composite Score
- average: 58.33

## Score Breakdown
- num_found: 2.41
- num_gold: 3.00
- partial_recall: 80.44
- recall: 58.33

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 1.166 | 1.115 | 1.665 |
| summarize_hop1 | 2.471 | 1.993 | 5.662 |
| query_hop2 | 2.119 | 1.151 | 3.258 |
| retrieve_hop2 | 1.143 | 1.360 | 1.661 |
| summarize_hop2 | 2.460 | 2.013 | 5.022 |
| query_hop3 | 1.539 | 1.085 | 2.925 |
| retrieve_hop3 | 1.305 | 1.508 | 1.666 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **12.202** | **10.500** | **21.118** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 125 |
