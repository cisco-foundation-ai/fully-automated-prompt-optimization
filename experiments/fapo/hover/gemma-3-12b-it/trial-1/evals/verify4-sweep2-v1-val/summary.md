# Evaluation Summary

Total cases: 300

## Composite Score
- average: 93.00

## Score Breakdown
- num_found: 2.93
- num_gold: 3.00
- num_missing: 0.07
- partial_recall: 97.67
- recall: 93.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 4.921 | 4.699 | 8.477 |
| summarize_hop1 | 1.732 | 1.407 | 3.686 |
| retrieve_hop2 | 8.855 | 9.092 | 13.650 |
| summarize_hop2 | 1.609 | 1.321 | 3.462 |
| retrieve_hop3 | 3.852 | 2.865 | 11.522 |
| summarize_hop3 | 1.332 | 1.054 | 2.912 |
| retrieve_hop4 | 1.846 | 1.516 | 5.845 |
| entity_sweep | 75.536 | 76.065 | 85.993 |
| combine_retrievals | 0.129 | 0.131 | 0.186 |
| **Total** | **99.813** | **98.457** | **123.262** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_sweep | 21 |
