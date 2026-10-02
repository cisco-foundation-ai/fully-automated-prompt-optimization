# Evaluation Summary

Total cases: 300

## Composite Score
- average: 60.67

## Score Breakdown
- exact_match: 60.67
- f1: 69.28

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 1.058 | 0.677 | 1.740 |
| summarize_hop1 | 2.194 | 2.008 | 3.686 |
| query_hop2 | 0.970 | 0.929 | 1.292 |
| retrieve_hop2 | 1.248 | 1.371 | 1.692 |
| summarize_hop2 | 2.806 | 2.644 | 4.529 |
| answer | 1.115 | 1.052 | 1.720 |
| **Total** | **9.391** | **9.247** | **13.331** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 118 |
