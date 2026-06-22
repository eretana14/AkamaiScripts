import os
import requests
from akamai.edgegrid import EdgeGridAuth
import configparser

# ========================
# CONFIGURATION
# ========================
EDGE_HOSTNAMES_TO_REMOVE = [
    "eretana-dsa2.vimorcr.com.edgekey.net",
    # Add more hostnames here as needed
]
ACCOUNT_SWITCH_KEY = "1-6JHGX:1-8BYUX"           # Set to None if not needed
CONTRACT_ID = "ctr_1-1NC95D"                     # Required for your account
GROUP_ID = "grp_243619"                          # Required for your account
EXACT_MATCH = True                               # True = exact match, False = partial match
DRY_RUN = False                                   # True = only list matches, no deletion
BATCH_MODE = False                               # True = deletes all matches without asking

EDGERC_PATH = "~/.edgerc"                        # Path to your .edgerc
EDGERC_SECTION = "terraform"                     # Section name in .edgerc

# ========================
# LOAD .EDGERC AND CREATE SESSION
# ========================
EDGERC_PATH = os.path.expanduser(EDGERC_PATH)

config = configparser.ConfigParser()
config.read(EDGERC_PATH)
print("Loaded sections:", config.sections())

session = requests.Session()
session.auth = EdgeGridAuth.from_edgerc(EDGERC_PATH, EDGERC_SECTION)

host = config.get(EDGERC_SECTION, "host")
base_url = f"https://{host}"
headers = {"Accept": "application/json"}

# ========================
# STEP 1: FETCH ALL EDGE HOSTNAMES
# ========================
print("📡 Fetching edge hostnames...")

params = {}
if ACCOUNT_SWITCH_KEY:
    params["accountSwitchKey"] = ACCOUNT_SWITCH_KEY
if CONTRACT_ID:
    params["contractId"] = CONTRACT_ID
if GROUP_ID:
    params["groupId"] = GROUP_ID

url = f"{base_url}/papi/v1/edgehostnames"
response = session.get(url, headers=headers, params=params)

if response.status_code != 200:
    print("❌ Failed to fetch edge hostnames:")
    print(response.text)
    exit(1)

data = response.json()
edge_hostnames = data.get("edgeHostnames", {}).get("items", [])
print(f"✅ Retrieved {len(edge_hostnames)} hostnames.")

# ========================
# STEP 2: FILTER MATCHES
# ========================
matches = []

for hostname in EDGE_HOSTNAMES_TO_REMOVE:
    for item in edge_hostnames:
        domain = item.get("edgeHostnameDomain", "")
        if EXACT_MATCH:
            if domain == hostname:
                matches.append(item)
        else:
            if hostname in domain:
                matches.append(item)

if not matches:
    print("🔍 No matching edge hostnames found.")
    exit(0)

print(f"\n🔍 Found {len(matches)} match(es):")
for m in matches:
    print(f"- {m['edgeHostnameId']} → {m['edgeHostnameDomain']}")

# ========================
# STEP 3: DELETE MATCHES
# ========================
if DRY_RUN:
    print("\n🧪 DRY RUN ENABLED — no deletions will be performed.")
    exit(0)

print("\n⚠️ Deletion mode enabled.")
if BATCH_MODE:
    print("🟢 Batch mode: all matches will be deleted automatically.\n")
else:
    print("⚠️ Interactive mode: confirm each deletion.\n")

for m in matches:
    edge_hostname_id_str = m["edgeHostnameId"]  # e.g., "ehn_6108891"
    try:
        edge_hostname_id = int(edge_hostname_id_str.split("_")[1])
    except Exception:
        print(f"❌ Invalid edgeHostnameId format for {edge_hostname_id_str}, skipping...")
        continue

    domain = m["edgeHostnameDomain"]

    # GET HAPI info
    get_url = f"{base_url}/hapi/v1/edge-hostnames/{edge_hostname_id}"
    get_params = {}
    if ACCOUNT_SWITCH_KEY:
        get_params["accountSwitchKey"] = ACCOUNT_SWITCH_KEY

    get_resp = session.get(get_url, headers=headers, params=get_params)
    if get_resp.status_code != 200:
        print(f"❌ Failed to retrieve edge hostname info for {domain}")
        print(get_resp.status_code, get_resp.text)
        continue

    info = get_resp.json()
    dns_zone = info.get("dnsZone")
    record_name = info.get("recordName")

    if not dns_zone or not record_name:
        print(f"❌ Could not determine dnsZone or recordName for {domain}, skipping...")
        continue

    # CONFIRMATION
    if not BATCH_MODE:
        confirm = input(f"\nDelete edge hostname '{domain}' ({edge_hostname_id})? (yes/no): ")
        if confirm.lower() not in ["yes", "y"]:
            print(f"⏭️ Skipped {domain}")
            continue

    # DELETE
    delete_url = f"{base_url}/hapi/v1/dns-zones/{dns_zone}/edge-hostnames/{record_name}"
    delete_params = {}
    if ACCOUNT_SWITCH_KEY:
        delete_params["accountSwitchKey"] = ACCOUNT_SWITCH_KEY

    delete_resp = session.delete(delete_url, headers=headers, params=delete_params)
    if delete_resp.status_code in [200, 204, 202]:  # 202 = queued
        print(f"✅ Submitted deletion for {domain} (status: {delete_resp.status_code})")
    else:
        print(f"❌ Failed to delete {domain}")
        print(delete_resp.status_code, delete_resp.text)

print("\n🏁 Script completed.")