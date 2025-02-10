# atlas-experiment-fetcher

A Python script for dynamically fetching and parsing experiment metadata from the EBI Gene Expression Atlas (GXA) API, generating structured outputs in YAML and TSV formats. 

The script retrieves experiment accessions, extracts key details such as organism, experiment type, and assay groups, and ensures properly formatted YAML for downstream processing.

This can be useful for researchers interested in listing and analysing all experiments available in GXA.

## Usage
Run the script with:
```
 python fetch_gxa_metadata.py gxa-studies.yaml gxa-studies.tsv
```
