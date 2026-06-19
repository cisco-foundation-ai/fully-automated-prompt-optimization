# Evaluation Summary

Total cases: 300

## Composite Score
- average: 66.67

## Score Breakdown
- exact_match: 66.67
- f1: 75.91

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.014 | 0.002 | 0.009 |
| summarize_hop1 | 6.063 | 5.393 | 11.438 |
| query_hop2 | 3.791 | 2.772 | 6.512 |
| retrieve_hop2 | 0.911 | 1.257 | 1.611 |
| summarize_hop2 | 5.426 | 4.896 | 9.238 |
| answer | 2.241 | 1.948 | 4.153 |
| **Total** | **18.446** | **17.065** | **28.369** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 100 |
