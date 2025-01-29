import subprocess
import json
from datetime import datetime

studyid_counter = 0
formatted_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# Fetch the list of experiment accessions dynamically from GXA API
def get_experiment_ids():
    bash_command = 'curl -sS https://www.ebi.ac.uk/gxa/json/experiments | jq -r ".experiments[].experimentAccession" | sort -u'
    experiment_accessions = subprocess.check_output(bash_command, shell=True, text=True)
    study_ids = experiment_accessions.strip().split("\n")

    return study_ids


def fetch_and_parse_data(study_id):
    study_url = f"https://www.ebi.ac.uk/gxa/json/experiments/{study_id}"

    # Use curl to fetch the data and jq to parse it
    curl_command = f"curl -sS {study_url} | jq '.'"
    data = subprocess.check_output(curl_command, shell=True)

    # Load data into python
    json_data = json.loads(data)

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
                print(f"      - contrast_description: \"{contrast_details.get('contrastDescription', 'N/A')}\"")

                # Collect and clean data for the contrast properties
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
                    test_value = prop.get("testValue", "N/A")

                    if property_name in cleaned_properties and test_value not in cleaned_properties[property_name]:
                        cleaned_properties[property_name].append(test_value)

                # print the cleaned properties
                for prop_name, prop_values in cleaned_properties.items():
                    if prop_values:
                        print(f"        {prop_name}: {', '.join(prop_values)}")

                # Print resources for visualisation if they exist
                for resource in contrast_details.get("resources", []):
                    resource_type = resource.get("type", "N/A")
                    resource_uri = resource.get("uri", "N/A")
                    print(f"        resource_type: {resource_type}")
                    print(f"        resource_uri: {resource_uri}")

    # Parse out the assay groups
    assay_groups = json_data.get("columnHeaders", [])

    # loop through assay groups and print relevant properties (ignoring "N/A" groups)
    for assay_group in assay_groups:
        assay_group_id = assay_group.get('assayGroupId', 'N/A')
        if assay_group_id != "N/A":
            print(f"      - assay_group_id: {assay_group_id}")

            # Extract properties and print relevant ones
            properties = assay_group.get("assayGroupSummary", {}).get("properties", [])
            found_factors = False

            for prop in properties:
                property_name = prop.get("propertyName", "").replace(" ", "_")
                test_value = prop.get("testValue", "")

                # Check if property is relevant, and print it
                if property_name in ["organism_part", "developmental_stage", "disease"]:
                    found_factors = True
                    print(f"        {property_name}: {test_value}")

            # If no relevant factors found, print a message
            if not found_factors:
                print("        No relevant factors found.")
        else:
            continue

# print YAML header with current date
print(f"date: {formatted_datetime}")

study_ids = get_experiment_ids()

print(f"experiment_count: {len(study_ids)}")
print("experiments:")

for study_id in study_ids:
    fetch_and_parse_data(study_id)
