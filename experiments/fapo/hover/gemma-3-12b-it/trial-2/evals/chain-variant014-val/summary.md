# Evaluation Summary

Total cases: 300

## Composite Score
- average: 63.33

## Score Breakdown
- num_found: 2.59
- num_gold: 3.00
- num_missing: 0.41
- partial_recall: 86.44
- recall: 63.33

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.005 | 0.002 | 0.004 |
| summarize_hop1 | 2.291 | 1.963 | 4.850 |
| query_hop2 | 0.360 | 0.303 | 0.712 |
| retrieve_hop2 | 0.745 | 0.003 | 1.633 |
| summarize_hop2 | 7.721 | 6.210 | 10.541 |
| query_hop3 | 0.399 | 0.345 | 0.715 |
| retrieve_hop3 | 1.275 | 1.563 | 1.672 |
| summarize_hop3 | 11.470 | 10.354 | 17.111 |
| query_hop4 | 0.417 | 0.357 | 0.741 |
| retrieve_hop4 | 1.384 | 1.585 | 1.676 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **26.066** | **23.181** | **34.020** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop4 | 110 |
