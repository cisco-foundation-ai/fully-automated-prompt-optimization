# Evaluation Summary

Total cases: 300

## Composite Score
- average: 17.67

## Score Breakdown
- num_found: 1.75
- num_gold: 3.00
- partial_recall: 58.33
- recall: 17.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.036 | 0.002 | 0.009 |
| summarize_hop1 | 1.631 | 1.265 | 2.316 |
| query_hop2 | 0.592 | 0.499 | 0.898 |
| retrieve_hop2 | 0.393 | 0.002 | 1.554 |
| summarize_hop2 | 1.874 | 1.684 | 3.154 |
| query_hop3 | 0.694 | 0.495 | 0.866 |
| retrieve_hop3 | 0.487 | 0.002 | 1.579 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **5.707** | **4.792** | **10.150** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 224 |
| query_hop2 | 29 |
| query_hop3 | 28 |
| retrieve_hop2 | 17 |
| summarize_hop2 | 17 |
