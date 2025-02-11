# Atlas Experiment Fetcher

A Python script for dynamically fetching and parsing experiment metadata from the EBI Gene Expression Atlas (GXA) API, generating structured outputs in YAML and TSV formats. 

The script retrieves experiment accessions, extracts key details such as organism, experiment type, and assay groups, and ensures properly formatted YAML for downstream processing.

Useful for researchers listing and analyzing all experiments available in GXA.

## Usage

To run the script, use the following command:

```sh
python fetch_gxa_metadata.py [<output_filename>]
```

For example:

```sh
python fetch_gxa_metadata.py gxa-studies
```

will generate the following files:

- `gxa-studies.yaml`
- `gxa-studies.tsv`

If the user does not specify an output filename, the script will generate `output.yaml` and `output.tsv` by default.
