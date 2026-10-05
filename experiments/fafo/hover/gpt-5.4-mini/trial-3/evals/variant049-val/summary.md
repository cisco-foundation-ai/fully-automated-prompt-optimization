# Evaluation Summary

Total cases: 300

## Composite Score
- average: 57.00

## Score Breakdown
- num_found: 2.52
- num_gold: 3.00
- num_missing: 0.48
- partial_recall: 83.89
- recall: 57.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.003 | 0.002 | 0.004 |
| summarize_hop1 | 3.271 | 2.974 | 5.464 |
| query_hop2 | 0.817 | 0.685 | 1.060 |
| retrieve_hop2 | 1.386 | 1.549 | 1.689 |
| summarize_hop2 | 3.296 | 2.785 | 6.324 |
| query_hop3 | 0.750 | 0.677 | 1.004 |
| retrieve_hop3 | 1.301 | 1.548 | 1.686 |
| combine_retrievals | 0.000 | 0.000 | 0.001 |
| **Total** | **10.825** | **10.158** | **16.387** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 129 |
