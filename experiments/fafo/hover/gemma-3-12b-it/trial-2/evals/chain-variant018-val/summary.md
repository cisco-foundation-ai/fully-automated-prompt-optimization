# Evaluation Summary

Total cases: 300

## Composite Score
- average: 69.67

## Score Breakdown
- num_found: 2.67
- num_gold: 3.00
- num_missing: 0.33
- partial_recall: 89.00
- recall: 69.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.004 | 0.002 | 0.006 |
| summarize_hop1 | 3.332 | 2.778 | 6.907 |
| query_hop2 | 0.366 | 0.332 | 0.623 |
| retrieve_hop2 | 0.620 | 0.003 | 1.641 |
| summarize_hop2 | 7.966 | 7.580 | 12.690 |
| query_hop3 | 0.393 | 0.342 | 0.689 |
| retrieve_hop3 | 0.600 | 0.002 | 1.649 |
| summarize_hop3 | 7.406 | 7.230 | 13.170 |
| query_hop4 | 0.488 | 0.438 | 0.880 |
| retrieve_hop4 | 1.453 | 1.569 | 1.716 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **22.629** | **21.483** | **33.787** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop4 | 91 |
