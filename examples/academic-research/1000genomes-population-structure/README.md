# 1000 Genomes Population Structure Clustering

**Who runs this:** Bioinformatics researchers, population geneticists, and
computational biology faculty studying human genetic diversity. This example
is also relevant for any researcher who needs to validate a clustering
approach against a dataset with known ground-truth groupings.

**What it does:** Clusters 1000 Genomes Project samples by genomic principal
components to recover the five major super-population groups (AFR, AMR, EAS,
EUR, SAS) — without writing a line of Python. A researcher might ask:
*"Load the 1000 Genomes PCA summary and cluster the samples into five
population groups."* Quick Suite finds the dataset on RODA, loads it, and
runs k-means (k=5, standardized) to produce cluster assignments per sample.

Because k-means on PCA components is a well-validated approach for population
stratification, this scenario also serves as a sanity check for the clustering
profile itself: if the five clusters don't correspond roughly to the known
super-populations, something is wrong with the input data or the preprocessing.

**Data:** 1000 Genomes Project on RODA (`s3://1000genomes/`). The project
sequenced 2,504 individuals across 26 populations from five continental
super-populations. This workflow operates on a **pre-processed PCA summary
table** with columns `sample_id`, `super_population`, and `pc1` through `pc5`.
The raw variant calls (multi-sample VCFs) are large and require PCA
preprocessing with tools like PLINK2 or HAIL before this workflow begins;
register the PCA output as a RODA-accessible path using the quick-suite-data
`register-source` Lambda. No IRB approval is required — 1000 Genomes data is
publicly consented for research use.

**Output:** A Parquet file at `result_uri` with each sample's `cluster_id`,
distance to centroid, and original PC columns. The named snapshot
`1000genomes-k5-superpopulations` enables re-running with different k values
and comparing results via `compute_compare` — useful for determining optimal k
on novel datasets where ground truth is unknown.

**Prerequisites:** A PCA summary table registered as a RODA-accessible S3
path (see Data section above). Stacks required: `data`, `compute`.
