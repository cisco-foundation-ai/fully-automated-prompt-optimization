# Evaluation Summary

Total cases: 300

## Composite Score
- average: 74.67

## Score Breakdown
- num_found: 2.72
- num_gold: 3.00
- partial_recall: 90.78
- recall: 74.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.009 | 0.002 | 0.009 |
| summarize_hop1 | 2.584 | 2.331 | 4.154 |
| query_hop2 | 0.931 | 0.771 | 1.595 |
| retrieve_hop2 | 0.625 | 0.002 | 1.620 |
| summarize_hop2 | 3.812 | 3.338 | 6.658 |
| query_hop3 | 1.040 | 0.778 | 1.992 |
| retrieve_hop3 | 1.075 | 1.289 | 1.633 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **10.076** | **9.389** | **15.277** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 76 |
