# atlas-experiment-fetcher

A Python script to dynamically fetch and parse experiment metadata from the EBI Gene Expression Atlas (GXA) API, outputting structured data in valid YAML format. The script retrieves experiment accessions, extracts key details such as organism, experiment type, and assay groups, and ensures properly formatted YAML for downstream processing.

This can be useful for researchers interested in listing and analysing all experiments available in GXA.

## Usage
Run the script and redirect the output to a YAML file:
```
 python pythonic-query.py > gxa-studies.yaml
```
