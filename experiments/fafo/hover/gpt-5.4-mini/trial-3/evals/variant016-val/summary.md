# Evaluation Summary

Total cases: 300

## Composite Score
- average: 22.67

## Score Breakdown
- num_found: 1.83
- num_gold: 3.00
- num_missing: 1.17
- partial_recall: 61.11
- recall: 22.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.017 | 0.002 | 0.009 |
| summarize_hop1 | 1.635 | 1.470 | 2.269 |
| query_hop2 | 0.942 | 0.731 | 1.138 |
| retrieve_hop2 | 1.055 | 1.271 | 1.602 |
| summarize_hop2 | 2.007 | 1.812 | 2.622 |
| query_hop3 | 0.850 | 0.714 | 1.007 |
| retrieve_hop3 | 1.027 | 1.268 | 1.615 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **7.534** | **7.099** | **11.211** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 232 |
