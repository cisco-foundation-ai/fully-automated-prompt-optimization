# Evaluation Summary

Total cases: 300

## Composite Score
- average: 69.33

## Score Breakdown
- exact_match: 69.33
- f1: 76.20

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.145 | 0.002 | 0.120 |
| summarize_hop1 | 1.603 | 1.411 | 2.785 |
| query_hop2 | 1.204 | 1.094 | 1.772 |
| retrieve_hop2 | 0.416 | 0.002 | 1.447 |
| summarize_hop2 | 1.688 | 1.592 | 2.647 |
| answer | 0.840 | 0.754 | 1.302 |
| **Total** | **5.897** | **5.288** | **9.599** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 92 |
