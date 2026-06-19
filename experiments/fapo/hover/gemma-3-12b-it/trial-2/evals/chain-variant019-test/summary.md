# Evaluation Summary

Total cases: 300

## Composite Score
- average: 72.67

## Score Breakdown
- num_found: 2.70
- num_gold: 3.00
- num_missing: 0.30
- partial_recall: 89.89
- recall: 72.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.003 | 0.002 | 0.008 |
| summarize_hop1 | 3.527 | 3.069 | 7.806 |
| query_hop2 | 0.374 | 0.331 | 0.612 |
| retrieve_hop2 | 0.992 | 1.292 | 1.661 |
| summarize_hop2 | 6.175 | 5.973 | 9.627 |
| query_hop3 | 0.392 | 0.349 | 0.628 |
| retrieve_hop3 | 1.354 | 1.352 | 1.672 |
| summarize_hop3 | 8.768 | 7.287 | 13.097 |
| query_hop4 | 0.477 | 0.438 | 0.647 |
| retrieve_hop4 | 1.361 | 1.365 | 1.683 |
| combine_retrievals | 0.000 | 0.000 | 0.001 |
| **Total** | **23.424** | **21.465** | **32.618** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop4 | 82 |
