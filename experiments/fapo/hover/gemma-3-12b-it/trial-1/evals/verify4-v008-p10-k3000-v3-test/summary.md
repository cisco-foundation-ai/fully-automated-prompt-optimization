# Evaluation Summary

Total cases: 300

## Composite Score
- average: 86.00

## Score Breakdown
- num_found: 2.85
- num_gold: 3.00
- num_missing: 0.15
- partial_recall: 95.11
- recall: 86.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 5.382 | 5.057 | 9.271 |
| summarize_hop1 | 1.580 | 1.344 | 3.400 |
| retrieve_hop2 | 8.583 | 9.189 | 14.471 |
| summarize_hop2 | 1.398 | 1.223 | 2.785 |
| retrieve_hop3 | 4.267 | 3.248 | 11.293 |
| summarize_hop3 | 1.324 | 1.145 | 2.477 |
| retrieve_hop4 | 2.144 | 1.660 | 6.418 |
| combine_retrievals | 0.051 | 0.044 | 0.117 |
| **Total** | **24.729** | **24.515** | **39.393** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop4_trunc | 42 |
