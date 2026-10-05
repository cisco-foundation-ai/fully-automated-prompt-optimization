# Evaluation Summary

Total cases: 300

## Composite Score
- average: 62.67

## Score Breakdown
- num_found: 2.60
- num_gold: 3.00
- num_missing: 0.40
- partial_recall: 86.67
- recall: 62.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.003 | 0.002 | 0.003 |
| summarize_hop1 | 3.435 | 2.892 | 7.057 |
| query_hop2 | 0.352 | 0.312 | 0.643 |
| retrieve_hop2 | 0.640 | 0.002 | 1.613 |
| summarize_hop2 | 8.174 | 7.723 | 12.921 |
| query_hop3 | 0.391 | 0.356 | 0.607 |
| retrieve_hop3 | 1.034 | 1.301 | 1.626 |
| summarize_hop3 | 13.277 | 11.905 | 19.384 |
| query_hop4 | 0.415 | 0.372 | 0.701 |
| retrieve_hop4 | 1.225 | 1.415 | 1.627 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **28.946** | **26.976** | **42.581** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop4 | 112 |
