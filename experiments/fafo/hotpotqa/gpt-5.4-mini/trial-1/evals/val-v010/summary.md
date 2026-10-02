# Evaluation Summary

Total cases: 300

## Composite Score
- average: 67.33

## Score Breakdown
- exact_match: 67.33
- f1: 76.06

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.101 | 0.002 | 0.122 |
| summarize_hop1 | 1.316 | 1.221 | 2.098 |
| query_hop2 | 1.060 | 1.002 | 1.536 |
| retrieve_hop2 | 0.669 | 0.002 | 1.666 |
| summarize_hop2 | 1.497 | 1.417 | 2.142 |
| answer | 0.761 | 0.720 | 1.120 |
| **Total** | **5.403** | **4.835** | **8.077** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 98 |
