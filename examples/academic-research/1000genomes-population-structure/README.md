# 1000 Genomes Population Structure Clustering

A bioinformatics researcher uses Quick Suite to cluster 1000 Genomes Project
samples by genomic principal components, recovering the five major
super-population groups (AFR, AMR, EAS, EUR, SAS) without writing a single
line of Python. The workflow searches the Registry of Open Data on AWS for
the 1000 Genomes dataset, loads a PCA summary table, and runs k-means
clustering (k=5, standardized) using the quick-suite-compute
`clustering-kmeans` profile.

**Data source:** 1000 Genomes Project on RODA (`s3://1000genomes/`). The
project sequenced 2,504 individuals across 26 populations. Raw variant calls
are large multi-sample VCFs; this example operates on a pre-processed PCA
summary table with columns `sample_id`, `super_population`, `pc1` through
`pc5`. PCA computation from raw VCFs (e.g., with PLINK2 or HAIL) is assumed
to have been run upstream and the result registered as a RODA-accessible S3
path. The `roda_search` and `roda_load` steps handle the discovery and Quick
Sight registration of that table.

**Output:** A Parquet file at `result_uri` with each sample's assigned
cluster label (`cluster_id`), distance to centroid, and the original PC
columns. The named snapshot `1000genomes-k5-superpopulations` is stored in
`qs-compute-snapshots` and can be compared against future runs (e.g., with
different k) via `compute_compare`.

**Prerequisites:** A pre-processed PCA summary table must be registered in
RODA or accessible via an S3 path that `roda_load` can reach. The raw 1000
Genomes VCF files on RODA are publicly available but require VCF-to-PCA
preprocessing before this workflow begins. Research computing staff can
register the PCA output path using the quick-suite-data `register-source`
internal Lambda. No IRB approval is required — 1000 Genomes data is publicly
consented for research use.
