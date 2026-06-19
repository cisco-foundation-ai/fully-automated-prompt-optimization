# Evaluation Summary

Total cases: 300

## Composite Score
- average: 64.33

## Score Breakdown
- exact_match: 64.33
- f1: 72.60

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.117 | 0.002 | 0.119 |
| summarize_hop1 | 1.186 | 1.101 | 1.818 |
| query_hop2 | 0.991 | 0.955 | 1.344 |
| retrieve_hop2 | 0.622 | 0.002 | 1.693 |
| summarize_hop2 | 1.151 | 1.074 | 1.783 |
| answer | 0.874 | 0.794 | 1.159 |
| **Total** | **4.941** | **4.133** | **7.430** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 107 |
