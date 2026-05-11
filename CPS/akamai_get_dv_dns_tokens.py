import csv
import os
import requests
from akamai.edgegrid import EdgeGridAuth, EdgeRc
from urllib.parse import urljoin

# --- CONFIGURATION ---
EDGERC_PATH = os.path.expanduser("~/.edgerc")
SECTION = "default"
CSV_FILE = "akamai_dns_challenges.csv"

# SET YOUR SEARCH CRITERIA
SEARCH_COMMON_NAME = "next.returnsunlimited.com"  # e.g., "www.yourdomain.com"
SEARCH_SLOT = 349698                 # e.g., 12345

# ACCOUNT SWITCH KEY
ACCOUNT_SWITCH_KEY = "F-AC-587797:1-2RBL" 

def get_dns_challenges():
    if not os.path.exists(EDGERC_PATH):
        print(f"Error: .edgerc file not found at {EDGERC_PATH}")
        return

    edgerc = EdgeRc(EDGERC_PATH)
    baseurl = f"https://{edgerc.get(SECTION, 'host')}"
    session = requests.Session()
    session.auth = EdgeGridAuth.from_edgerc(edgerc, SECTION)

    params = {}
    if ACCOUNT_SWITCH_KEY:
        params['accountSwitchKey'] = ACCOUNT_SWITCH_KEY

    print(f"Searching for enrollment (Account: {ACCOUNT_SWITCH_KEY if ACCOUNT_SWITCH_KEY else 'Default'})...")
    
    # 1. Get all enrollments
    list_url = urljoin(baseurl, "/cps/v2/enrollments")
    # Using v11+json to ensure we get the most metadata
    list_res = session.get(
        list_url, 
        params=params, 
        headers={"Accept": "application/vnd.akamai.cps.enrollments.v11+json"}
    )
    
    if list_res.status_code != 200:
        print(f"Failed to list enrollments: {list_res.status_code}")
        print(list_res.text)
        return

    enrollments = list_res.json().get("enrollments", [])
    target_enrollment = None

    for ent in enrollments:
        cn_match = SEARCH_COMMON_NAME and ent.get("commonName") == SEARCH_COMMON_NAME
        slot_match = SEARCH_SLOT and str(SEARCH_SLOT) in [str(s) for s in ent.get("assignedSlots", [])]
        
        if cn_match or slot_match:
            target_enrollment = ent
            break

    if not target_enrollment:
        print("Could not find a matching certificate enrollment.")
        return

    # --- FIX START ---
    # 2. Extract IDs safely
    # Handle Enrollment ID
    enrollment_loc = target_enrollment.get('location', '')
    enrollment_id = enrollment_loc.split('/')[-1]
    
    pending_changes = target_enrollment.get("pendingChanges", [])
    if not pending_changes:
        print(f"No pending changes found for {target_enrollment.get('commonName')}.")
        return
    
    # Handle Change ID (Fixing the 'dict' vs 'str' issue)
    last_change = pending_changes[-1]
    if isinstance(last_change, dict):
        change_loc = last_change.get('location', '')
    else:
        change_loc = last_change
        
    change_id = change_loc.split('/')[-1]
    # --- FIX END ---

    print(f"Found Enrollment: {enrollment_id} | Active Change: {change_id}")

    # 3. Fetch DNS Challenges
    challenge_url = urljoin(baseurl, f"/cps/v2/enrollments/{enrollment_id}/changes/{change_id}/input/info/lets-encrypt-challenges")
    headers = {"Accept": "application/vnd.akamai.cps.dv-challenges.v2+json"}
    
    response = session.get(challenge_url, params=params, headers=headers)

    if response.status_code != 200:
        print(f"Error fetching challenges: {response.status_code}\n{response.text}")
        return

    data = response.json()
    challenges_to_export = []

    if "dv" in data:
        for entry in data["dv"]:
            domain = entry.get("domain")
            for challenge in entry.get("challenges", []):
                if challenge.get("type") == "dns-01":
                    challenges_to_export.append({
                        "Record Name": f"_acme-challenge.{domain}",
                        "TTL": "60",
                        "Type": "TXT",
                        "Value": challenge.get("responseBody")
                    })

    if challenges_to_export:
        keys = challenges_to_export[0].keys()
        with open(CSV_FILE, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(challenges_to_export)
        print(f"Successfully exported {len(challenges_to_export)} records to {CSV_FILE}")
    else:
        print("No DNS-01 challenges found.")

if __name__ == "__main__":
    get_dns_challenges()