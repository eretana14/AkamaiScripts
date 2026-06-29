#!/usr/bin/env python3
import os
import sys
import csv
import requests
from akamai.edgegrid import EdgeGridAuth, EdgeRc

# ==========================================
# --- CONFIGURATION & USER VARIABLES ---
# ==========================================
EDGERC_PATH = os.path.expanduser("~/.edgerc")
EDGERC_SECTION = "default"
OUTPUT_CSV = "properties_using_siteshield.csv"

# Set your SiteShield Map ID here
TARGET_MAP_ID = "s470.akamaiedge.net"

# Set your Account Switch Key here
ACCOUNT_SWITCH_KEY = "F-AC-1889191:1-2RBL"

# FALLBACK: If expired contracts are completely hidden by the API but visible in your UI, 
# explicitly define them here (using the 'ctr_' prefix) to force the script to scan them.
# Example: FORCE_SCAN_CONTRACTS = ["ctr_P-39PY5AF"]
FORCE_SCAN_CONTRACTS = ["ctr_P-39PY5AF"]
# ==========================================

def init_session():
    """Initializes the Akamai EdgeGrid authenticated requests session."""
    if not os.path.exists(EDGERC_PATH):
        print(f"[-] Error: .edgerc file not found at {EDGERC_PATH}")
        sys.exit(1)
    try:
        edgerc = EdgeRc(EDGERC_PATH)
        session = requests.Session()
        session.auth = EdgeGridAuth.from_edgerc(edgerc, section=EDGERC_SECTION)
        base_host = edgerc.get(EDGERC_SECTION, "host")
        return base_host, session
    except Exception as e:
        print(f"[-] Error parsing edgerc or initializing session: {e}")
        sys.exit(1)

def make_request(session, method, url, headers=None, params=None):
    """Utility wrapper for API requests including standard headers."""
    if headers is None:
        headers = {}
    headers.update({
        "Accept": "application/json",
        "PAPI-Use-Prefixes": "true"
    })
    
    try:
        response = session.request(method, url, headers=headers, params=params)
        
        # Return status code alongside JSON so we can handle 403s/400s specifically
        if response.status_code == 200:
            return response.status_code, response.json()
        else:
            return response.status_code, None
            
    except Exception as e:
        print(f"[!] Error making request to {url}: {e}")
        return None, None

def find_siteshield_in_rules(rule_node, target_map_id):
    """Recursively parses the rule tree JSON structure to find the siteShield behavior."""
    if not rule_node:
        return False

    behaviors = rule_node.get("behaviors", [])
    for behavior in behaviors:
        if behavior.get("name") == "siteShield":
            options = behavior.get("options", {})
            ssmap = options.get("ssmap", {})
            
            map_value = ""
            if isinstance(ssmap, dict):
                map_value = str(ssmap.get("value", ""))
            else:
                map_value = str(ssmap)
            
            if target_map_id.strip().lower() in map_value.lower():
                return True

    children = rule_node.get("children", [])
    for child in children:
        if find_siteshield_in_rules(child, target_map_id):
            return True

    return False

def main():
    print("=== Akamai SiteShield Property Audit ===")
    print(f"[*] Target SiteShield Map: {TARGET_MAP_ID}")
    if ACCOUNT_SWITCH_KEY:
        print(f"[*] Account Switch Key:    {ACCOUNT_SWITCH_KEY}")
    
    print("\n[*] Authenticating with Akamai EdgeGrid...")
    base_host, session = init_session()
    
    query_params = {}
    if ACCOUNT_SWITCH_KEY:
        query_params["accountSwitchKey"] = ACCOUNT_SWITCH_KEY
        
    # Step 1: Extract Group mappings
    print("[*] Retrieving account groups...")
    status, groups_data = make_request(session, "GET", f"https://{base_host}/papi/v1/groups", params=query_params)
    if status != 200 or not groups_data or "groups" not in groups_data:
        print(f"[-] Failed to retrieve account groups (HTTP {status}).")
        sys.exit(1)
        
    # Step 2: Extract ALL Contracts natively (Active & Expired)
    print("[*] Retrieving master contract list...")
    status, contracts_data = make_request(session, "GET", f"https://{base_host}/papi/v1/contracts", params=query_params)
    
    group_items = groups_data["groups"].get("items", [])
    contract_items = contracts_data["contracts"].get("items", []) if contracts_data and "contracts" in contracts_data else []

    known_groups = [g.get("groupId") for g in group_items]
    all_contracts = [c.get("contractId") for c in contract_items]
    
    # Merge any manually provided override contracts
    for user_ctr in FORCE_SCAN_CONTRACTS:
        if user_ctr and user_ctr not in all_contracts:
            all_contracts.append(user_ctr)

    scan_targets = []
    mapped_contracts = set()

    # Map the "Active" pairs that Akamai willingly provided
    for item in group_items:
        g_id = item.get("groupId")
        for c_id in item.get("contractIds", []):
            scan_targets.append({"contractId": c_id, "groupId": g_id, "type": "Active"})
            mapped_contracts.add(c_id)

    # Find "Orphaned" expired contracts that Akamai hid from the group mappings
    orphaned_contracts = set(all_contracts) - mapped_contracts

    # Brute-force orphaned contracts against all known groups
    for o_c in orphaned_contracts:
        for g_id in known_groups:
            scan_targets.append({"contractId": o_c, "groupId": g_id, "type": "Expired/Orphaned"})

    print(f"[+] Discovered {len(known_groups)} active groups and {len(all_contracts)} total contracts.")
    print(f"[+] Total Contract/Group combinations queued to scan: {len(scan_targets)}\n")
    
    matching_properties = []
    
    # Step 3: Traverse combinations to inspect properties
    for idx, target in enumerate(scan_targets, start=1):
        contract_id = target["contractId"]
        group_id = target["groupId"]
        c_type = target["type"]
        
        print(f"[{idx}/{len(scan_targets)}] Scanning Contract: {contract_id} ({c_type}) | Group: {group_id}...")
        
        prop_params = query_params.copy()
        prop_params.update({"contractId": contract_id, "groupId": group_id})
        
        props_url = f"https://{base_host}/papi/v1/properties"
        status, props_data = make_request(session, "GET", props_url, params=prop_params)
        
        # Gracefully skip if an orphaned contract fails against an incorrect group ID
        if status in [400, 403, 404]:
            continue
            
        if status != 200 or not props_data or "properties" not in props_data:
            continue
            
        properties = props_data["properties"].get("items", [])
        
        for prop in properties:
            prop_id = prop.get("propertyId")
            prop_name = prop.get("propertyName")
            
            prod_version = prop.get("productionVersion")
            staging_version = prop.get("stagingVersion")
            latest_version = prop.get("latestVersion")
            
            if prod_version:
                version_to_check = prod_version
                network_status = "Active (Production)"
            elif staging_version:
                version_to_check = staging_version
                network_status = "Active (Staging)"
            else:
                version_to_check = latest_version
                network_status = "Inactive (Draft)"
            
            if not version_to_check:
                continue
                
            rules_url = f"https://{base_host}/papi/v1/properties/{prop_id}/versions/{version_to_check}/rules"
            r_status, rules_data = make_request(session, "GET", rules_url, params=prop_params)
            
            if r_status != 200 or not rules_data or "rules" not in rules_data:
                continue
                
            uses_target_map = find_siteshield_in_rules(rules_data.get("rules"), TARGET_MAP_ID)
            
            if uses_target_map:
                print(f"  -> [MATCH] '{prop_name}' uses Map '{TARGET_MAP_ID}' | Status: {network_status} | Contract: {contract_id}")
                matching_properties.append({
                    "Property Name": prop_name,
                    "Property ID": prop_id,
                    "Contract ID": contract_id,
                    "Group ID": group_id,
                    "Version Checked": version_to_check,
                    "Network Status": network_status
                })
                    
    # Step 4: Export results
    if matching_properties:
        print(f"\n[*] Compiling entries into {OUTPUT_CSV}...")
        try:
            with open(OUTPUT_CSV, mode="w", newline="", encoding="utf-8") as csv_file:
                fieldnames = ["Property Name", "Property ID", "Contract ID", "Group ID", "Version Checked", "Network Status"]
                writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
                writer.writeheader()
                for row in matching_properties:
                    writer.writerow(row)
            print(f"[+] Success! CSV file generated: {os.path.abspath(OUTPUT_CSV)}")
        except Exception as csv_err:
            print(f"[-] Failed to generate CSV output: {csv_err}")
    else:
        print(f"\n[-] No properties found actively using SiteShield Map matching '{TARGET_MAP_ID}'.")

if __name__ == "__main__":
    main()