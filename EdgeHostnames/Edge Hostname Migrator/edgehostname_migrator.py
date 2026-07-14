import csv
import os
import sys
import time
import requests
from akamai.edgegrid import EdgeGridAuth, EdgeRc
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

# Recognized Akamai edge hostname suffixes (used for patching validation)
AKAMAI_SUFFIXES = [
    '.edgekey.net', '.edgesuite.net', '.akamaized.net', 
    '.edgekey-staging.net', '.edgesuite-staging.net'
]

def parse_edge_hostname(edge_hostname):
    """Splits a full edge hostname into (record_name, dns_zone) for HAPI patching."""
    edge_hostname = edge_hostname.strip().lower()
    for suffix in AKAMAI_SUFFIXES:
        if edge_hostname.endswith(suffix):
            record_name = edge_hostname[:-len(suffix)]
            dns_zone = suffix.lstrip('.')
            return record_name, dns_zone
    return None, None

def setup_akamai_session(edgerc_section="default"):
    """Initializes the authenticated EdgeGrid session with smart retries."""
    edgerc_path = os.path.expanduser("~/.edgerc")
    if not os.path.exists(edgerc_path):
        print(f"❌ Error: .edgerc file not found at {edgerc_path}")
        sys.exit(1)
        
    edgerc = EdgeRc(edgerc_path)
    session = requests.Session()
    session.auth = EdgeGridAuth.from_edgerc(edgerc, edgerc_section)
    
    retries = Retry(
        total=5,
        backoff_factor=2,
        status_forcelist=[429, 502, 503, 504],
        raise_on_status=False
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("https://", adapter)
    
    base_url = f"https://{edgerc.get(edgerc_section, 'host')}"
    return session, base_url

def phase_1_discovery(session, base_url, output_csv, account_switch_key):
    """
    Phase 1: Automated Account Scan
    Queries the account groups structure, loops contracts, and isolates 
    all edge hostnames currently locked to IPv4-only.
    """
    print(f"\n🚀 Starting Phase 1: Account-Wide Discovery Scan")
    print(f"🔍 Traversing account topology via PAPI...")
    
    params = {}
    if account_switch_key:
        params['accountSwitchKey'] = account_switch_key
        
    headers = {'Accept': 'application/json'}
    
    # Step A: Pull account groups
    groups_url = f"{base_url}/papi/v1/groups"
    try:
        response = session.get(groups_url, params=params, headers=headers)
        if response.status_code != 200:
            print(f"❌ Failed to fetch account groups. Status: {response.status_code}, Msg: {response.text}")
            sys.exit(1)
        groups_data = response.json().get('groups', {}).get('items', [])
    except Exception as e:
        print(f"💥 Network error fetching groups: {e}")
        sys.exit(1)
        
    if not groups_data:
        print("⚠️ No organizational groups or contracts found inside this account context.")
        return

    ipv4_only_hostnames = {}
    scanned_combos = set()

    print(f"📋 Identified {len(groups_data)} group nodes. Deep-scanning for hostnames...")
    
    # Step B: Scan all group-contract intersections to gather edge hostnames
    for group in groups_data:
        group_id = group.get('groupId')
        group_name = group.get('groupName', 'Unknown')
        contract_ids = group.get('contractIds', [])
        
        for contract_id in contract_ids:
            combo_key = f"{group_id}::{contract_id}"
            if combo_key in scanned_combos:
                continue
            scanned_combos.add(combo_key)
            
            print(f"  🔎 Querying Group: '{group_name}' | Contract: {contract_id}...")
            
            ehn_url = f"{base_url}/papi/v1/edgehostnames"
            ehn_params = {'contractId': contract_id, 'groupId': group_id}
            if account_switch_key:
                ehn_params['accountSwitchKey'] = account_switch_key
                
            try:
                ehn_response = session.get(ehn_url, params=ehn_params, headers=headers)
                if ehn_response.status_code == 200:
                    items = ehn_response.json().get('edgeHostnames', {}).get('items', [])
                    for item in items:
                        hostname = item.get('edgeHostnameDomain')
                        ip_behavior = item.get('ipVersionBehavior', 'UNKNOWN')
                        
                        if hostname and ip_behavior == 'IPV4':
                            # Dynamic allocation cleanly deduplicates cross-contract mappings
                            ipv4_only_hostnames[hostname] = 'IPV4'
                else:
                    pass
            except Exception as e:
                print(f"    ⚠️ Warning parsing map {combo_key}: {e}")
                
            time.sleep(0.2)  # Pacing read operations safely

    # Step C: Log out file for manual confirmation
    if ipv4_only_hostnames:
        print(f"\n🎯 Discovery Finished! Found {len(ipv4_only_hostnames)} hostnames with IPv6 disabled.")
        with open(output_csv, mode='w', newline='', encoding='utf-8') as outfile:
            writer = csv.DictWriter(outfile, fieldnames=['edge_hostname', 'current_behavior'])
            writer.writeheader()
            for hn, behavior in ipv4_only_hostnames.items():
                writer.writerow({'edge_hostname': hn, 'current_behavior': behavior})
        print(f"📝 Auto-generated action plan saved to: '{output_csv}'")
    else:
        print("\n✅ Clean sweep! Every edge hostname in this account is already running Dual-Stack.")

def phase_2_update(session, base_url, update_csv, account_switch_key):
    """
    Phase 2: Targeted Migration Patching
    Reads the audited CSV list and executes asynchronous edge-hostname updates.
    """
    print(f"\n🚀 Starting Phase 2: Targeted Dual-Stack Migration")
    print(f"📖 Parsing verified list from: {update_csv}")
    
    if not os.path.exists(update_csv):
        print(f"❌ Error: Targets file '{update_csv}' missing. Please run Phase 1 discovery first.")
        sys.exit(1)

    params = {}
    if account_switch_key:
        params['accountSwitchKey'] = account_switch_key

    headers = {'Content-Type': 'application/json-patch+json'}
    
    # Crucial Fix applied here: changed payload value to 'IPV6_IPV4_DUALSTACK'
    patch_body = [
        {
            "op": "replace", 
            "path": "/ipVersionBehavior", 
            "value": "IPV6_IPV4_DUALSTACK"
        }
    ]

    with open(update_csv, mode='r', encoding='utf-8') as infile:
        reader = csv.DictReader(infile)
        if 'edge_hostname' not in reader.fieldnames:
            print("❌ Error: Targeted CSV is missing required 'edge_hostname' column structure.")
            sys.exit(1)

        for row in reader:
            hostname = row.get('edge_hostname')
            if not hostname:
                continue
                
            record_name, dns_zone = parse_edge_hostname(hostname)
            if not record_name:
                print(f"⚠️ Skipping row. Entry '{hostname}' does not match known Akamai edge patterns.")
                continue
            
            url = f"{base_url}/hapi/v1/dns-zones/{dns_zone}/edge-hostnames/{record_name}"
            try:
                response = session.patch(url, json=patch_body, headers=headers, params=params)
                if response.status_code in [200, 202, 204]:
                    print(f"🚀 Dual-Stack change requested & queued: {hostname}")
                else:
                    print(f"❌ Rejected {hostname}. Status: {response.status_code}, Msg: {response.text}")
            except Exception as e:
                print(f"💥 Communication failure updating {hostname}: {e}")
            
            time.sleep(2.0)  # Defensive pacing to completely prevent rate limits during updates
            
    print(f"\n🎉 Migration deployment processing sequence complete!")

if __name__ == "__main__":
    # ==========================================
    #          GLOBAL VARIABLE CONTROLS
    # ==========================================
    ACCOUNT_SWITCH_KEY = "1-6JHGX:1-8BYUX"      
    EDGERC_SECTION = "default"          
    TARGET_MIGRATION_FILE = "discovered_ipv4_hostnames.csv"
    # ==========================================

    session, base_url = setup_akamai_session(EDGERC_SECTION)
    
    if len(sys.argv) > 1 and sys.argv[1] == "--phase2":
        confirm = input(f"⚠️ Confirm executing Phase 2 bulk migration targeting entries in '{TARGET_MIGRATION_FILE}'? (yes/no): ")
        if confirm.strip().lower() == 'yes':
            phase_2_update(session, base_url, TARGET_MIGRATION_FILE, ACCOUNT_SWITCH_KEY)
        else:
            print("❌ Process halted.")
    else:
        phase_1_discovery(session, base_url, TARGET_MIGRATION_FILE, ACCOUNT_SWITCH_KEY)