# Evaluation Summary

Total cases: 300

## Composite Score
- average: 85.67

## Score Breakdown
- num_found: 2.85
- num_gold: 3.00
- num_missing: 0.15
- partial_recall: 95.00
- recall: 85.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 5.325 | 5.000 | 8.904 |
| summarize_hop1 | 1.509 | 1.281 | 3.186 |
| retrieve_hop2 | 7.802 | 7.973 | 14.028 |
| summarize_hop2 | 1.386 | 1.210 | 2.836 |
| retrieve_hop3 | 3.254 | 2.796 | 8.290 |
| summarize_hop3 | 1.288 | 1.125 | 2.599 |
| retrieve_hop4 | 1.687 | 1.470 | 4.820 |
| combine_retrievals | 0.042 | 0.036 | 0.084 |
| **Total** | **22.293** | **21.773** | **34.536** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop4_trunc | 43 |
