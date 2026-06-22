import requests
import csv
import datetime
from akamai.edgegrid import EdgeGridAuth, EdgeRc
from urllib.parse import urljoin

# ==============================================================================
# CONFIGURATION
# ==============================================================================
# Manually specify your Account Switch Key here (e.g., "1-ABC12"). 
# Leave it as an empty string "" if you want to use the default account access.
#ACCOUNT_SWITCH_KEY = "YOUR_ACCOUNT_SWITCH_KEY_HERE"
ACCOUNT_SWITCH_KEY = "1-1D2F:1-2RBL"

# ==============================================================================

# 1. Setup Authentication
try:
    edgerc = EdgeRc('~/.edgerc')
    section = 'default'
    baseurl = f"https://{edgerc.get(section, 'host')}"
except Exception as e:
    print(f"Error reading .edgerc file: {e}")
    exit(1)

session = requests.Session()
session.auth = EdgeGridAuth.from_edgerc(edgerc, section)

def get_papi_data(path, params=None):
    """Helper to handle API requests with the manual Account Switch Key and PAPI headers."""
    if params is None:
        params = {}
    
    # Inject the manual account switch key if provided
    if ACCOUNT_SWITCH_KEY.strip():
        params['accountSwitchKey'] = ACCOUNT_SWITCH_KEY.strip()
        
    url = urljoin(baseurl, path)
    headers = {
        "PAPI-Use-Prefixes": "true", 
        "Accept": "application/json"
    }
    
    response = session.get(url, params=params, headers=headers)
    
    if response.status_code != 200:
        print(f"Error fetching {path}: {response.status_code} - {response.text}")
        return None
    return response.json()

def main():
    if ACCOUNT_SWITCH_KEY.strip():
        print(f"--- Acting on Manual Account Switch Key: {ACCOUNT_SWITCH_KEY.strip()} ---")
    else:
        print("--- No manual account switch key specified, using default account access ---")
    
    all_edge_hostnames = {}  # Map ID -> Domain
    used_edge_hostname_ids = set()

    # 2. Get all Groups and Contracts
    print("Fetching Groups...")
    groups_data = get_papi_data("/papi/v1/groups")
    if not groups_data:
        return

    groups = groups_data.get("groups", {}).get("items", [])

    for group in groups:
        group_id = group['groupId']
        contract_id = group['contractIds'][0]
        query_params = {"contractId": contract_id, "groupId": group_id}

        # 3. List all Edge Hostnames in this group
        print(f"Scanning Group: {group_id} for Edge Hostnames...")
        ehn_data = get_papi_data("/papi/v1/edgehostnames", params=query_params)
        if ehn_data:
            for ehn in ehn_data.get("edgeHostnames", {}).get("items", []):
                all_edge_hostnames[ehn['edgeHostnameId']] = ehn['edgeHostnameDomain']

        # 4. List all Properties in this group
        print(f"Scanning Group: {group_id} for Properties...")
        properties_data = get_papi_data("/papi/v1/properties", params=query_params)
        if properties_data:
            for prop in properties_data.get("properties", {}).get("items", []):
                prop_id = prop['propertyId']
                # Check the latest version to identify used EHNs
                v_path = f"/papi/v1/properties/{prop_id}/versions/{prop['latestVersion']}/hostnames"
                host_data = get_papi_data(v_path, params=query_params)
                
                if host_data:
                    for host_item in host_data.get("hostnames", {}).get("items", []):
                        if 'edgeHostnameId' in host_item:
                            used_edge_hostname_ids.add(host_item['edgeHostnameId'])

    # 5. Identify Unused EHNs
    unused_output = []
    for ehn_id, domain in all_edge_hostnames.items():
        if ehn_id not in used_edge_hostname_ids:
            unused_output.append({
                "Edge Hostname ID": ehn_id, 
                "Edge Hostname Domain": domain
            })

    # 6. Generate filename with timestamp
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M")
    output_filename = f"unused_edge_hostnames_{timestamp}.csv"

    # 7. Save to CSV
    if unused_output:
        with open(output_filename, 'w', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=["Edge Hostname ID", "Edge Hostname Domain"])
            writer.writeheader()
            writer.writerows(unused_output)
        print(f"\n--- Process Complete ---")
        print(f"Success! Found {len(unused_output)} unused edge hostnames.")
        print(f"Results exported to: {output_filename}")
    else:
        print("\nAll edge hostnames in this account are currently associated with properties.")

if __name__ == "__main__":
    main()