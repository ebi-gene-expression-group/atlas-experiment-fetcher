from datetime import datetime
import time
import subprocess
import json
import requests

studyid_counter = 0
formatted_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
gxa_url = f"https://www.ebi.ac.uk/gxa/json/experiments/"

def clean_text(text):
    if isinstance(text, str):
        text = text.replace(" :", "").replace(": ", "").replace(":", "")  # remove misplaced colons
        text = text.replace('"', "'")  # replace double quotes with single quotes
        text = text.lstrip(", ")  # remove leading commas and spaces
        if text.startswith(">"):  # ensure '>' values are properly quoted
            text = f'"{text}"'
    return text


# remove duplicate keys in properties
def remove_duplicates(properties):
    unique_properties = {}
    for prop_name, prop_values in properties.items():
        unique_properties[prop_name] = list(set(prop_values))
    return unique_properties


# fetch the list of experiment accessions dynamically from GXA API
def get_experiment_ids():
    bash_command = 'curl -sS https://www.ebi.ac.uk/gxa/json/experiments | jq -r ".experiments[].experimentAccession" | sort -u'
    experiment_accessions = subprocess.check_output(bash_command, shell=True, text=True)
    study_ids = experiment_accessions.strip().split("\n")

    return study_ids


def fetch_and_parse_data(study_id):
    study_url = f"https://www.ebi.ac.uk/gxa/json/experiments/{study_id}"

    max_retries = 5
    retry_delay = 5
    attempt = 0

    while attempt < max_retries:
        try:
            response = requests.get(study_url)
            response.raise_for_status()

            # check if the response is empty or not valid JSON
            if not response.text.strip():
                attempt += 1
                time.sleep(retry_delay)
                continue

            # try to load the json data from the response
            try:
                json_data = response.json()
            except json.JSONDecodeError:
                attempt += 1
                time.sleep(retry_delay)
                continue

            # if json is valid, process the data
            if isinstance(json_data, dict) and "experiment" in json_data:
                break

        except requests.RequestException:
            attempt += 1
            time.sleep(retry_delay)

    experiment_type = json_data.get("experiment", {}).get("type", "N/A")
    organism = json_data.get("experiment", {}).get("species", "N/A")

    global studyid_counter
    studyid_counter += 1

    # print study header
    print(f"  - accession_count: {studyid_counter}")
    print(f"    accession: {study_id}")
    print(f"    experiment_type: {experiment_type}")
    print(f"    organism: {organism}")
    print("    assay_groups:")

    # check if it's a differential experiment, and print contrast details
    if "differential" in experiment_type.lower():
        contrast_summary = json_data.get("columnHeaders", [])

        # loop through contrast summary and print only relevant details
        for column in contrast_summary:
            contrast_details = column.get("contrastSummary", {})
            if contrast_details:
                print(f"      - contrast_description: \"{clean_text(contrast_details.get('contrastDescription', 'N/A'))}\"")

                # collect and clean data for contrast properties
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

                    if property_name in cleaned_properties and test_value not in cleaned_properties[property_name]:
                        cleaned_properties[property_name].append(test_value)

                # remove duplicate properties
                cleaned_properties = remove_duplicates(cleaned_properties)

                # print the cleaned properties
                for prop_name, prop_values in cleaned_properties.items():
                    if prop_values:
                        # remove None, empty strings, whitespace-only values, and accidental commas
                        cleaned_values = [v.strip() for v in prop_values if v and v.strip() and not v.strip().startswith(",")]

                        if cleaned_values:
                            print(f"        {prop_name}: {', '.join(cleaned_values)}")

                for resource in contrast_details.get("resources", []):
                    resource_type = clean_text(resource.get("type", "N/A"))
                    resource_uri = clean_text(resource.get("uri", "N/A"))
                    print(f"        resource_type: {resource_type}")
                    print(f"        resource_uri: {resource_uri}")

    # parse out the assay groups
    assay_groups = json_data.get("columnHeaders", [])

    # loop through assay groups and print relevant properties (ignoring "N/A" groups)
    for assay_group in assay_groups:
        assay_group_id = assay_group.get('assayGroupId', 'N/A')
        if assay_group_id != "N/A":
            print(f"      - assay_group_id: {assay_group_id}")

            # extract properties and print relevant ones
            properties = assay_group.get("assayGroupSummary", {}).get("properties", [])
            cleaned_properties = {}

            for prop in properties:
                property_name = prop.get("propertyName", "").replace(" ", "_")
                test_value = clean_text(prop.get("testValue", ""))

                if property_name and test_value:
                    if property_name not in cleaned_properties:
                        cleaned_properties[property_name] = set()
                    cleaned_properties[property_name].add(test_value)

            for property_name, property_values in cleaned_properties.items():
                if property_values:
                    print(f"        {property_name}: {', '.join(property_values)}")

        else:
            continue


# print YAML header with current date
print("---")
print(f"date: {formatted_datetime}")

study_ids = get_experiment_ids()

print(f"experiment_count: {len(study_ids)}")
print("experiments:")

for study_id in study_ids:
    fetch_and_parse_data(study_id)
