# Evaluation Summary

Total cases: 300

## Composite Score
- average: 26.67

## Score Breakdown
- num_found: 1.93
- num_gold: 3.00
- num_missing: 1.07
- partial_recall: 64.44
- recall: 26.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 1.153 | 1.126 | 1.721 |
| summarize_hop1 | 3.288 | 1.881 | 5.238 |
| query_hop2 | 2.512 | 1.270 | 4.226 |
| retrieve_hop2 | 0.954 | 1.257 | 1.640 |
| summarize_hop2 | 3.919 | 2.215 | 7.018 |
| query_hop3 | 1.597 | 1.196 | 3.553 |
| retrieve_hop3 | 1.132 | 1.346 | 1.666 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **14.555** | **10.744** | **26.084** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 220 |
