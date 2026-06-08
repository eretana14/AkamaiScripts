import csv
import os
import sys
import requests
from akamai.edgegrid import EdgeGridAuth, EdgeRc

# --- CONFIGURATION ---
EDGERC_PATH = "~/.edgerc"
EDGERC_SECTION = "default"         
ACCOUNT_SWITCH_KEY = "1-6JHGX:1-8BYUX"    
INPUT_CSV_PATH = "zones.csv"
REPORT_CSV_PATH = "dns_changes_report.csv"
RECORD_TYPE = "TXT"
DEFAULT_TTL = 300
# ---------------------


def get_edgegrid_session():
    """Initializes the authenticated Akamai EdgeGrid session."""
    try:
        expanded_path = os.path.expanduser(EDGERC_PATH)
        rc = EdgeRc(expanded_path)
        session = requests.Session()
        session.auth = EdgeGridAuth.from_edgerc(rc, EDGERC_SECTION)
        return session, rc.get(EDGERC_SECTION, "host")
    except Exception as e:
        print(f"❌ Error loading edgerc profile: {e}")
        sys.exit(1)


def get_accessible_zones(session, base_url, params):
    """
    Pre-flight check: Fetches ALL zones accessible under this accountSwitchKey
    using showAll=true to prevent API pagination clipping.
    """
    print("🔍 Fetching list of authorized zones from Akamai to validate account access...")
    
    validation_params = params.copy()
    validation_params["showAll"] = "true"
    
    try:
        response = session.get(base_url, params=validation_params)
        if response.status_code == 200:
            zones_data = response.json().get("zones", [])
            accessible_set = {z.get("zone", "").lower().strip() for z in zones_data}
            print(f"✅ Successfully cached {len(accessible_set)} zones from your Akamai profile.")
            return accessible_set
        else:
            print(f"❌ Failed to retrieve account zone registry (HTTP {response.status_code}): {response.text}")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Network exception occurred validating zone access: {e}")
        sys.exit(1)


def fetch_change_plan(session, base_url, params, valid_zones_set):
    """
    Phase 1: Validates access permissions, checks record existence on Akamai,
    and constructs the safe local CSV layout proposal.
    """
    print("\n=== PHASE 1: Scanning zones and generating change report ===")
    plan = []

    if not os.path.exists(INPUT_CSV_PATH):
        print(f"❌ Input file error: Could not find the file '{INPUT_CSV_PATH}'")
        sys.exit(1)

    with open(INPUT_CSV_PATH, mode="r", encoding="utf-8-sig") as csvfile:
        reader = csv.DictReader(csvfile)
        
        if not all(h in reader.fieldnames for h in ["zone", "record_name", "record_value"]):
            print("❌ CSV Header error: Your input file must contain 'zone', 'record_name', and 'record_value' columns.")
            sys.exit(1)

        for row in reader:
            zone = row["zone"].strip()
            zone_lower = zone.lower()
            record_name = row["record_name"].strip().lower()
            new_value = row["record_value"].strip()

            if zone_lower not in valid_zones_set:
                print(f"⚠️ ACCESS DENIED/NOT FOUND: '{zone}' is not visible under account key {ACCOUNT_SWITCH_KEY}. Skipping entirely.")
                continue

            if not new_value.startswith('"'):
                new_value = f'"{new_value}"'

            record_url = f"{base_url}/{zone}/names/{record_name}/types/{RECORD_TYPE}"
            
            try:
                response = session.get(record_url, params=params)
            except Exception as e:
                print(f"⚠️ Connection error checking {record_name} in {zone}: {e}. Skipping.")
                continue

            action = "CREATE"
            current_rdata = []
            ttl = DEFAULT_TTL

            if response.status_code == 200:
                action = "UPDATE"
                data = response.json()
                current_rdata = data.get("rdata", [])
                ttl = data.get("ttl", DEFAULT_TTL)
            elif response.status_code == 404:
                action = "CREATE"
            else:
                print(f"⚠️ Error checking record {record_name} in {zone} (HTTP {response.status_code}). Skipping.")
                continue

            if new_value in current_rdata:
                action = "NO_CHANGE"
                proposed_rdata = current_rdata
            else:
                proposed_rdata = current_rdata + [new_value]

            plan.append({
                "zone": zone,
                "record_name": record_name,
                "action": action,
                "ttl": ttl,
                "current_values": " | ".join(current_rdata),
                "proposed_values": " | ".join(proposed_rdata),
                "new_value_to_add": new_value
            })
            print(f"  Processed {zone} -> Target Action: {action}")

    with open(REPORT_CSV_PATH, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["zone", "record_name", "action", "ttl", "current_values", "proposed_values", "new_value_to_add"])
        writer.writeheader()
        writer.writerows(plan)

    print(f"\n✅ Scan complete. Change summary layout generated at: {REPORT_CSV_PATH}")
    return plan


def execute_change_plan(session, base_url, params, plan):
    """Phase 2: Performs modifications. Zone activations occur natively on write calls."""
    print("\n=== PHASE 2: Executing changes ===")
    
    success_count = 0
    failure_count = 0

    for item in plan:
        zone = item["zone"]
        record_name = item["record_name"]
        action = item["action"]
        ttl = item["ttl"]

        if action == "NO_CHANGE":
            print(f"⏭️ Skipping {zone} (Record already contains this validation value).")
            continue

        record_url = f"{base_url}/{zone}/names/{record_name}/types/{RECORD_TYPE}"
        proposed_rdata = [v.strip() for v in item["proposed_values"].split("|")]

        payload = {
            "name": record_name,
            "type": RECORD_TYPE,
            "ttl": ttl,
            "rdata": proposed_rdata
        }

        try:
            if action == "UPDATE":
                print(f"🔄 Updating record for {zone}...")
                resp = session.put(record_url, params=params, json=payload)
            else:
                print(f"➕ Creating new record for {zone}...")
                resp = session.post(record_url, params=params, json=payload)
            
            if resp.status_code in [200, 201, 204]:
                print(f"  └ 🎉 Data written successfully. Akamai has queued the zone activation.")
                success_count += 1
            else:
                print(f"❌ Failed to modify record on zone {zone} (HTTP {resp.status_code}): {resp.text.strip()}")
                failure_count += 1
                
        except Exception as e:
            print(f"❌ Exception caught writing modifications for {zone}: {e}")
            failure_count += 1

    print("\n" + "=" * 40)
    print("RUN FINAL STATUS COMPLETION:")
    print(f" Successfully Changed & Queue-Activated: {success_count} zones")
    print(f" Encountered Failures: {failure_count} zones")
    print("=" * 40)


def main():
    session, base_host = get_edgegrid_session()
    base_url = f"https://{base_host}/config-dns/v2/zones"
    params = {"accountSwitchKey": ACCOUNT_SWITCH_KEY}

    valid_zones_set = get_accessible_zones(session, base_url, params)
    plan = fetch_change_plan(session, base_url, params, valid_zones_set)

    creates = sum(1 for i in plan if i["action"] == "CREATE")
    updates = sum(1 for i in plan if i["action"] == "UPDATE")
    skips = sum(1 for i in plan if i["action"] == "NO_CHANGE")

    print("\n" + "=" * 40)
    print("PLAN PROPOSAL METRICS SUMMARY:")
    print(f" - Records to Create: {creates}")
    print(f" - Records to Append Data Into (Update): {updates}")
    print(f" - Records matched perfectly (Will Skip): {skips}")
    print("=" * 40)
    print(f"💡 Action required: Please open '{REPORT_CSV_PATH}' and audit the plan details.")

    user_input = input("\nDo you want to proceed with executing these changes across Akamai networks? (yes/no): ").strip().lower()

    if user_input == "yes":
        execute_change_plan(session, base_url, params, plan)
    else:
        print("\n❌ Operation aborted. No configurations were changed or activated on Akamai.")


if __name__ == "__main__":
    main()