# Evaluation Summary

Total cases: 300

## Composite Score
- average: 72.67

## Score Breakdown
- num_found: 2.70
- num_gold: 3.00
- partial_recall: 90.00
- recall: 72.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.025 | 0.002 | 0.013 |
| summarize_hop1 | 2.288 | 2.186 | 3.392 |
| query_hop2 | 0.905 | 0.711 | 1.117 |
| retrieve_hop2 | 0.536 | 0.002 | 1.578 |
| summarize_hop2 | 3.454 | 3.107 | 5.561 |
| query_hop3 | 0.854 | 0.725 | 1.572 |
| retrieve_hop3 | 0.470 | 0.002 | 1.448 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **8.532** | **8.096** | **12.748** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 82 |
