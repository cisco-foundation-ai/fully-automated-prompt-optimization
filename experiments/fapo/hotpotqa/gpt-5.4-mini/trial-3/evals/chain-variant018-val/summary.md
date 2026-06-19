# Evaluation Summary

Total cases: 300

## Composite Score
- average: 72.67

## Score Breakdown
- exact_match: 72.67
- f1: 79.39

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.033 | 0.002 | 0.006 |
| summarize_hop1 | 1.218 | 1.147 | 1.686 |
| query_hop2 | 1.041 | 0.935 | 1.580 |
| retrieve_hop2 | 0.642 | 0.002 | 1.651 |
| summarize_hop2 | 1.209 | 1.159 | 1.564 |
| answer | 0.926 | 0.831 | 1.384 |
| **Total** | **5.069** | **4.511** | **6.740** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 80 |
| query_hop2 | 2 |
