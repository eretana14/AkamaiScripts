import csv
import os
import requests
from akamai.edgegrid import EdgeGridAuth, EdgeRc

# ==================== CONFIGURATION ====================
EDGERC_PATH = os.path.expanduser("~/.edgerc")
EDGERC_SECTION = "default"  # Change if your credentials are under a different section

# Akamai Security Configuration Details
CONFIG_ID = 100757                        # Your Security Configuration ID
POLICY_ID = "1234_255276"                 # Your Security Policy ID
ACCOUNT_SWITCH_KEY = "B-M-1YX7F48:1-8BYUX" # Your Account Switch Key

CSV_FILE_PATH = "hostnames.csv"
# =======================================================

def get_akamai_session():
    """Initializes and returns an authenticated Akamai API session."""
    if not os.path.exists(EDGERC_PATH):
        raise FileNotFoundError(f"EdgeRc file not found at {EDGERC_PATH}")
    
    edgerc = EdgeRc(EDGERC_PATH)
    base_url = edgerc.get(EDGERC_SECTION, "host")
    
    session = requests.Session()
    session.auth = EdgeGridAuth.from_edgerc(edgerc, section=EDGERC_SECTION)
    
    return session, f"https://{base_url}"

def read_hostnames_from_csv(file_path):
    """Reads hostnames from a CSV file and skips the header row."""
    hostnames = []
    with open(file_path, mode='r', encoding='utf-8') as file:
        reader = csv.reader(file)
        next(reader, None)  # Skips the 'hostname' header row
        for row in reader:
            if row:
                hostnames.append(row[0].strip())
    return hostnames

def main():
    # 1. Initialize Session and read CSV
    print("Initializing Akamai Session...")
    session, base_url = get_akamai_session()
    
    print(f"Reading hostnames from {CSV_FILE_PATH}...")
    hostnames_to_add = read_hostnames_from_csv(CSV_FILE_PATH)
    print(f"Loaded {len(hostnames_to_add)} hostnames.")

    # Setup query parameters
    params = {}
    if ACCOUNT_SWITCH_KEY:
        params['accountSwitchKey'] = ACCOUNT_SWITCH_KEY

    # 2. Get the latest version of the Security Configuration
    print(f"Fetching latest version for Config ID: {CONFIG_ID}...")
    version_url = f"{base_url}/appsec/v1/configs/{CONFIG_ID}/versions"
    res = session.get(version_url, params=params)
    res.raise_for_status()
    
    versions = res.json().get("versionList", [])
    if not versions:
        raise Exception("No configuration versions found.")
    latest_version = max(v['version'] for v in versions)
    print(f"Current latest version is: {latest_version}")

    # 3. Clone the configuration to create a new editable version
    print(f"Cloning version {latest_version} to create a new draft...")
    clone_payload = {
        "createFromVersion": latest_version,
        "ruleUpdate": False
    }
    res = session.post(version_url, params=params, json=clone_payload)
    res.raise_for_status()
    
    new_version = res.json().get("version")
    print(f"Successfully created new version draft: {new_version}")

    # 4. Add Hostnames to the Configuration's Selected Hostnames list
    print(f"Appending hostnames to Configuration Version {new_version}...")
    selected_hosts_url = f"{base_url}/appsec/v1/configs/{CONFIG_ID}/versions/{new_version}/selected-hostnames"
    
    hosts_payload = {
        "hostnameList": [{"hostname": host} for host in hostnames_to_add],
        "mode": "append"
    }
    res = session.put(selected_hosts_url, params=params, json=hosts_payload)
    res.raise_for_status()
    print("Hostnames successfully appended to the configuration layer.")

    # 5. Find the Match Target linked to our Policy ID
    print(f"Retrieving match targets for version {new_version}...")
    match_targets_url = f"{base_url}/appsec/v1/configs/{CONFIG_ID}/versions/{new_version}/match-targets"
    res = session.get(match_targets_url, params=params)
    res.raise_for_status()
    
    raw_response = res.json()
    match_targets_container = raw_response.get("matchTargets", {})
    website_targets = match_targets_container.get("websiteTargets", []) if isinstance(match_targets_container, dict) else []
    
    target_to_update = None
    
    if isinstance(website_targets, list):
        for target in website_targets:
            if isinstance(target, dict):
                target_type = target.get("type")
                associated_policy_id = target.get("securityPolicy", {}).get("policyId") if target.get("securityPolicy") else None
                
                if target_type == "website" and associated_policy_id == POLICY_ID:
                    target_to_update = target
                    break

    if not target_to_update:
        raise Exception(f"Could not find an existing Website Match Target linked to policy: {POLICY_ID}")
        
    target_id = target_to_update["targetId"]
    print(f"Found Website Match Target (ID: {target_id}) for policy '{POLICY_ID}'.")

    # 6. Update the Website Match Target to include the new hostnames
    print(f"Updating Match Target {target_id} with new hostnames...")
    specific_target_url = f"{base_url}/appsec/v1/configs/{CONFIG_ID}/versions/{new_version}/match-targets/{target_id}"
    
    # Grab existing items safely to maintain state
    current_target_hostnames = target_to_update.get("hostnames", [])
    if not isinstance(current_target_hostnames, list):
        current_target_hostnames = []
        
    file_paths = target_to_update.get("filePaths", ["/*"])
    default_file = target_to_update.get("defaultFile", "NO_MATCH")
    
    # Merge lists uniquely
    updated_hostnames_list = list(set(current_target_hostnames + hostnames_to_add))
    
    # Rebuild full tracking configuration payload to appease schema verification
    target_payload = {
        "type": "website",
        "hostnames": updated_hostnames_list,
        "filePaths": file_paths,
        "defaultFile": default_file,
        "securityPolicy": {
            "policyId": POLICY_ID
        }
    }
    
    res = session.put(specific_target_url, params=params, json=target_payload)
    res.raise_for_status()
    
    print("-" * 50)
    print(f"SUCCESS: {len(hostnames_to_add)} hostnames successfully onboarded!")
    print(f"A new Security Configuration version ({new_version}) has been prepared.")
    print(f"Hostnames are now explicitly mapped via Match Target {target_id} to policy '{POLICY_ID}'.")
    print("Please review the changes in the Akamai Control Center and activate when ready.")
    print("-" * 50)

if __name__ == "__main__":
    try:
        main()
    except requests.exceptions.HTTPError as err:
        print(f"\nAPI Error Occurred: {err}")
        if err.response is not None:
            print(f"Response Details: {err.response.text}")
    except Exception as e:
        print(f"\nAn error occurred: {e}")