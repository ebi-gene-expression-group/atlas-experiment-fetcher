from datetime import datetime
import time
import subprocess
import json
import requests
import yaml
import pandas as pd
import argparse
import sys

MAX_RETRIES = 5
RETRY_DELAY = 5
GXA_URL = "https://www.ebi.ac.uk/gxa/json/experiments/"

if len(sys.argv) != 3:
    print("Usage: python fetch_gxa_metadata.py <output_yaml_filename> <output_tsv_filename>")
    sys.exit(1)

parser = argparse.ArgumentParser(description="Generate and save experiment data to YAML and tsv")
parser.add_argument("yaml_filename", help="Output Yaml filename")
parser.add_argument("tsv_filename", help="Output Tsv filename")
args = parser.parse_args()


def clean_text(text):
    '''Cleans and formats text by removing colons, adjusting quotes, and handling special cases'''
    if isinstance(text, str):
        text = text.replace(" :", "").replace(": ", "").replace(":", "")
        text = text.replace('"', "'")
        text = text.lstrip(", ")
        if text.startswith(">"):
            text = f'"{text}"'
    return text


def remove_duplicates(properties):
    '''Removes duplicate values in dictionary lists, ensuring unique entries'''
    return {k: list(set(v)) for k, v in properties.items() if v}


def get_experiment_ids():
    '''Fetches and returns a sorted list of experiment accession IDs from the GXA api'''
    bash_command = f'curl -sS {GXA_URL} | jq -r ".experiments[].experimentAccession" | sort -u'
    experiment_accessions = subprocess.check_output(bash_command, shell=True, text=True)
    return experiment_accessions.strip().split("\n")


def fetch_and_parse_data(study_id, studyid_counter):
    '''Fetches experiment data from GXA api, parses the JSON response, and extracts relevant details'''
    study_url = f"{GXA_URL}{study_id}"
    attempt = 0

    while attempt < MAX_RETRIES:
        try:
            response = requests.get(study_url)
            response.raise_for_status()

            # check if the response is empty or not valid JSON
            if not response.text.strip():
                attempt += 1
                time.sleep(RETRY_DELAY)
                continue

            # try to load the json data from the response
            try:
                json_data = response.json()
            except json.JSONDecodeError:
                attempt += 1
                time.sleep(RETRY_DELAY)
                continue

            # if json is valid, process the data
            if isinstance(json_data, dict) and "experiment" in json_data:
                break

        except requests.RequestException:
            attempt += 1
            time.sleep(RETRY_DELAY)

    experiment_type = json_data.get("experiment", {}).get("type", "N/A")
    organism = json_data.get("experiment", {}).get("species", "N/A")

    study_data = {
        "accession_count": studyid_counter,
        "accession": study_id,
        "experiment_type": experiment_type,
        "organism": organism,
        "assay_groups": []
    }

    if "differential" in experiment_type.lower():
        contrast_summary = json_data.get("columnHeaders", [])

        # loop through contrast summary and get only relevant details
        for column in contrast_summary:
            contrast_details = column.get("contrastSummary", {})
            if contrast_details:
                assay_group = {"contrast_description": clean_text(contrast_details.get("contrastDescription", "N/A"))}
                cleaned_properties = {
                    "clinical_information": [],
                    "disease": [],
                    "age": [],
                    "array_design": [],
                    "developmental_stage": [],
                    "individual": [],
                    "organism_part": [],
                    "sex": []
                }
                for prop in contrast_details.get("properties", []):
                    property_name = prop.get("propertyName", "N/A").replace(" ", "_")
                    test_value = clean_text(prop.get("testValue", "N/A"))
                    if property_name in cleaned_properties and test_value:
                        cleaned_properties[property_name].append(test_value)

                # remove duplicate properties
                cleaned_properties = remove_duplicates(cleaned_properties)
                assay_group.update({k: v for k, v in cleaned_properties.items() if v})
                for resource in contrast_details.get("resources", []):
                    assay_group["resource_type"] = clean_text(resource.get("type", "N/A"))
                    assay_group["resource_uri"] = clean_text(resource.get("uri", "N/A"))
                study_data["assay_groups"].append(assay_group)

    # parse out the assay groups
    assay_groups = json_data.get("columnHeaders", [])

    # loop through assay groups and get relevant properties (ignoring "N/A" groups)
    for assay_group in assay_groups:
        assay_group_id = assay_group.get('assayGroupId', 'N/A')
        if assay_group_id != "N/A":

            # get properties and print relevant ones
            properties = assay_group.get("assayGroupSummary", {}).get("properties", [])
            cleaned_properties = {}
            for prop in properties:
                property_name = prop.get("propertyName", "").replace(" ", "_")
                test_value = clean_text(prop.get("testValue", ""))
                if property_name and test_value:
                    cleaned_properties.setdefault(property_name, set()).add(test_value)
            filtered_properties = {k: list(v) for k, v in cleaned_properties.items() if v}
            if filtered_properties:
                filtered_properties["assay_group_id"] = assay_group_id
                study_data["assay_groups"].append(filtered_properties)
    return study_data


def flatten_dict(d, parent_key='', sep='_', keep_keys=None):
    '''Recursively flattens a nested dictionary, keeping only specific keys and joining duplicates'''

    if keep_keys is None:
        keep_keys = ['organism_part', 'developmental_stage', 'disease']

    items = {}
    for k, v in d.items():
        if isinstance(v, dict):
            # flatten nested dictionaries recursively
            items.update(flatten_dict(v, parent_key=f"{parent_key}{sep}{k}" if parent_key else k, sep=sep, keep_keys=keep_keys))
        elif isinstance(v, list):
            if all(isinstance(i, dict) for i in v):
                for idx, sub_dict in enumerate(v):
                    for sub_k, sub_v in sub_dict.items():
                        if sub_k in keep_keys:
                            new_key = f"{parent_key}{sep}{k}_{sub_k}"
                            if new_key not in items:
                                items[new_key] = set()
                            items[new_key].update(sub_v)
            else:
                items[f"{parent_key}{sep}{k}" if parent_key else k] = "; ".join(map(str, v))
        else:
            items[f"{parent_key}{sep}{k}" if parent_key else k] = v

    # join sets into sorted strings
    for key in items:
        if isinstance(items[key], set):
            items[key] = "; ".join(sorted(items[key]))

    return items


formatted_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
study_ids = get_experiment_ids()
experiments = []

for idx, study_id in enumerate(study_ids, 1):
    experiments.append(fetch_and_parse_data(study_id, idx))

yaml_data = {
    "date": formatted_datetime,
    "experiment_count": len(study_ids),
    "experiments": experiments
}

with open(args.yaml_filename, "w") as yaml_file:
    yaml.dump(
        yaml_data,
        yaml_file,
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=False,
        indent=2,
        explicit_start=True,
        width=200
    )


# define the keys to keep in TSV file
keep_keys = ['organism_part', 'developmental_stage', 'disease', 'age', 'genotype', 'sex']

flat_data = []
for exp in yaml_data.get("experiments", []):
    flat_exp = flatten_dict(exp, keep_keys=keep_keys)
    flat_data.append(flat_exp)

df = pd.DataFrame(flat_data)

df.to_csv(args.tsv_filename, sep="\t", index=False)
