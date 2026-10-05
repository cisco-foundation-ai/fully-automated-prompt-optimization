# Evaluation Summary

Total cases: 150

## Composite Score
- average: 47.33

## Score Breakdown
- exact_match: 47.33
- f1: 52.23

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.017 | 0.002 | 0.013 |
| summarize_hop1 | 1.209 | 1.104 | 1.625 |
| query_hop2 | 1.201 | 1.144 | 1.677 |
| retrieve_hop2 | 1.555 | 1.587 | 1.744 |
| summarize_hop2 | 1.207 | 1.195 | 1.633 |
| answer | 0.984 | 0.911 | 1.581 |
| **Total** | **6.174** | **5.832** | **7.849** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 79 |
