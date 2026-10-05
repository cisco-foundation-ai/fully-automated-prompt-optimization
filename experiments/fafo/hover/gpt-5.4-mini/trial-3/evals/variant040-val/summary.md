# Evaluation Summary

Total cases: 300

## Composite Score
- average: 46.67

## Score Breakdown
- num_found: 2.34
- num_gold: 3.00
- num_missing: 0.66
- partial_recall: 78.00
- recall: 46.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 1.013 | 0.608 | 1.720 |
| summarize_hop1 | 2.036 | 1.901 | 3.306 |
| query_hop2 | 0.927 | 0.722 | 1.635 |
| retrieve_hop2 | 1.427 | 1.489 | 1.679 |
| summarize_hop2 | 2.463 | 2.240 | 4.063 |
| query_hop3 | 0.833 | 0.731 | 1.120 |
| retrieve_hop3 | 1.392 | 1.457 | 1.693 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **10.091** | **9.518** | **13.918** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 160 |
