# Evaluation Summary

Total cases: 300

## Composite Score
- average: 86.67

## Score Breakdown
- num_found: 2.86
- num_gold: 3.00
- num_missing: 0.14
- partial_recall: 95.44
- recall: 86.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 4.888 | 4.446 | 8.482 |
| summarize_hop1 | 1.567 | 1.321 | 3.364 |
| retrieve_hop2 | 7.432 | 7.588 | 13.245 |
| summarize_hop2 | 1.362 | 1.198 | 2.600 |
| retrieve_hop3 | 2.691 | 2.357 | 6.444 |
| summarize_hop3 | 1.265 | 1.103 | 2.547 |
| retrieve_hop4 | 1.486 | 1.361 | 4.425 |
| combine_retrievals | 0.042 | 0.039 | 0.077 |
| **Total** | **20.734** | **19.997** | **31.748** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop4_trunc | 40 |
