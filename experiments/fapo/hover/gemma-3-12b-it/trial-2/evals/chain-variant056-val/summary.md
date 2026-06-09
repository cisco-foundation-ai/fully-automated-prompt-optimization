# Evaluation Summary

Total cases: 300

## Composite Score
- average: 79.00

## Score Breakdown
- num_found: 2.76
- num_gold: 3.00
- num_missing: 0.24
- partial_recall: 92.11
- recall: 79.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.003 | 0.002 | 0.010 |
| summarize_hop1 | 3.343 | 2.880 | 6.304 |
| query_hop2 | 0.404 | 0.331 | 0.665 |
| retrieve_hop2 | 0.680 | 0.009 | 1.582 |
| summarize_hop2 | 7.205 | 5.995 | 11.653 |
| query_hop3 | 0.570 | 0.418 | 1.636 |
| retrieve_hop3 | 2.637 | 2.599 | 3.213 |
| summarize_hop3 | 8.054 | 6.416 | 11.270 |
| query_hop4 | 0.543 | 0.428 | 1.308 |
| retrieve_hop4 | 1.352 | 1.453 | 1.638 |
| query_hop5 | 0.572 | 0.467 | 1.184 |
| retrieve_hop5 | 2.128 | 2.464 | 3.161 |
| combine_retrievals | 0.000 | 0.000 | 0.001 |
| **Total** | **27.491** | **24.695** | **34.845** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop5 | 63 |
