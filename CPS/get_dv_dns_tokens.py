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
# Update these to match the certificate you are looking for
SEARCH_COMMON_NAME = "next.returnsunlimited.com"  #This can be modified to any other common name 
SEARCH_SLOT = 349698                  # This can be modified to any other certificate slot 

def get_dns_challenges():
    if not os.path.exists(EDGERC_PATH):
        print(f"Error: .edgerc file not found at {EDGERC_PATH}")
        return

    # Initialize Akamai EdgeGrid Authentication
    edgerc = EdgeRc(EDGERC_PATH)
    baseurl = f"https://{edgerc.get(SECTION, 'host')}"
    session = requests.Session()
    session.auth = EdgeGridAuth.from_edgerc(edgerc, SECTION)

    print(f"Searching for enrollment: {SEARCH_COMMON_NAME if SEARCH_COMMON_NAME else SEARCH_SLOT}...")
    
    # 1. Get all enrollments
    list_url = urljoin(baseurl, "/cps/v2/enrollments")
    list_res = session.get(
        list_url, 
        headers={"Accept": "application/vnd.akamai.cps.enrollments.v11+json"}
    )
    
    if list_res.status_code != 200:
        print(f"Failed to list enrollments: {list_res.status_code}")
        print(list_res.text)
        return

    enrollments = list_res.json().get("enrollments", [])
    target_enrollment = None

    # Find the specific enrollment by Common Name or Slot
    for ent in enrollments:
        cn_match = SEARCH_COMMON_NAME and ent.get("commonName") == SEARCH_COMMON_NAME
        slot_match = SEARCH_SLOT and str(SEARCH_SLOT) in [str(s) for s in ent.get("assignedSlots", [])]
        
        if cn_match or slot_match:
            target_enrollment = ent
            break

    if not target_enrollment:
        print("Could not find a matching certificate enrollment.")
        return

    # 2. Extract IDs safely (handling both string and dictionary responses)
    enrollment_loc = target_enrollment.get('location', '')
    enrollment_id = enrollment_loc.split('/')[-1]
    
    pending_changes = target_enrollment.get("pendingChanges", [])
    if not pending_changes:
        print(f"No pending changes found for {target_enrollment.get('commonName')}. It may already be validated.")
        return
    
    # Check if the last change is a dict or a string
    last_change = pending_changes[-1]
    change_loc = last_change.get('location', '') if isinstance(last_change, dict) else last_change
    change_id = change_loc.split('/')[-1]

    print(f"Found Enrollment: {enrollment_id} | Active Change: {change_id}")

    # 3. Fetch DNS Challenges
    challenge_url = urljoin(baseurl, f"/cps/v2/enrollments/{enrollment_id}/changes/{change_id}/input/info/lets-encrypt-challenges")
    headers = {"Accept": "application/vnd.akamai.cps.dv-challenges.v2+json"}
    
    response = session.get(challenge_url, headers=headers)

    if response.status_code != 200:
        print(f"Error fetching challenges: {response.status_code}\n{response.text}")
        return

    data = response.json()
    challenges_to_export = []

    # 4. Filter for DNS TXT records (dns-01)
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

    # 5. Export to CSV
    if challenges_to_export:
        keys = challenges_to_export[0].keys()
        with open(CSV_FILE, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(challenges_to_export)
        print(f"Successfully exported {len(challenges_to_export)} DNS records to {CSV_FILE}")
    else:
        print("No DNS-01 (TXT) challenges found for this certificate change.")

if __name__ == "__main__":
    get_dns_challenges()