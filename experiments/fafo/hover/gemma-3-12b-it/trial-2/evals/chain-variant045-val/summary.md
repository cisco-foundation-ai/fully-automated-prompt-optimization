# Evaluation Summary

Total cases: 300

## Composite Score
- average: 78.67

## Score Breakdown
- num_found: 2.76
- num_gold: 3.00
- num_missing: 0.24
- partial_recall: 92.11
- recall: 78.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.003 | 0.002 | 0.005 |
| summarize_hop1 | 3.180 | 2.701 | 6.519 |
| query_hop2 | 0.434 | 0.326 | 0.961 |
| retrieve_hop2 | 0.798 | 0.520 | 1.590 |
| summarize_hop2 | 7.392 | 6.009 | 10.435 |
| query_hop3 | 0.512 | 0.378 | 1.410 |
| retrieve_hop3 | 2.745 | 2.655 | 3.204 |
| summarize_hop3 | 7.399 | 6.840 | 13.506 |
| query_hop4 | 0.551 | 0.421 | 1.607 |
| retrieve_hop4 | 1.300 | 1.337 | 1.651 |
| query_hop5 | 0.573 | 0.468 | 1.020 |
| retrieve_hop5 | 2.009 | 1.682 | 3.231 |
| combine_retrievals | 0.000 | 0.000 | 0.001 |
| **Total** | **26.895** | **25.339** | **36.927** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop5 | 64 |
