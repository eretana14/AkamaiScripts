import requests
import csv
from concurrent.futures import ThreadPoolExecutor
from akamai.edgegrid import EdgeGridAuth, EdgeRc

# -------------------------
# CONFIGURATION
# -------------------------

EDGERC_PATH = "~/.edgerc"
SECTION = "default"

# Removed ACCOUNT_SWITCH_KEY variable

zones = [
    "p6.arpa",
]

MAX_THREADS = 5

# -------------------------
# AUTHENTICATION
# -------------------------

edgerc = EdgeRc(EDGERC_PATH)
base_url = f"https://{edgerc.get(SECTION, 'host')}"

session = requests.Session()
session.auth = EdgeGridAuth.from_edgerc(edgerc, SECTION)

headers = {"Accept": "application/json"}

# -------------------------
# API CALLS
# -------------------------

def get_zone_info(zone):

    url = f"{base_url}/config-dns/v2/zones/{zone}"

    # Removed accountSwitchKey from params
    params = {}

    r = session.get(url, headers=headers, params=params)

    if r.status_code != 200:
        print(f"Zone info error for {zone}: {r.text}")
        return None

    return r.json()


def get_tsig_key(zone):

    url = f"{base_url}/config-dns/v2/zones/{zone}/key"

    # Removed accountSwitchKey from params
    params = {}

    r = session.get(url, headers=headers, params=params)

    if r.status_code == 404:
        return None

    if r.status_code != 200:
        print(f"TSIG error for {zone}: {r.text}")
        return None

    return r.json()


def fetch_records(zone):

    page = 1
    page_size = 1000
    records = []

    while True:

        url = f"{base_url}/config-dns/v2/zones/{zone}/recordsets"

        # Removed accountSwitchKey from params
        params = {
            "page": page,
            "pageSize": page_size
        }

        r = session.get(url, headers=headers, params=params)

        if r.status_code != 200:
            print(f"Record fetch error {zone}: {r.text}")
            break

        data = r.json()

        recordsets = data.get("recordsets", [])

        if not recordsets:
            break

        records.extend(recordsets)

        page += 1

    return records


# -------------------------
# CSV WRITERS
# -------------------------

def write_records(zone, records, zone_type):

    filename = f"{zone}_zone_records.csv"

    with open(filename, "w", newline="") as f:

        writer = csv.writer(f)

        writer.writerow([
            "zone",
            "zone_type",
            "name",
            "record_type",
            "ttl",
            "value"
        ])

        for record in records:

            name = record.get("name")
            rtype = record.get("type")
            ttl = record.get("ttl")

            for value in record.get("rdata", []):
                writer.writerow([zone, zone_type, name, rtype, ttl, value])

    print(f"Created {filename}")


def write_tsig(zone, tsig):

    if not tsig:
        return

    filename = f"{zone}_zone_tsig.csv"

    with open(filename, "w", newline="") as f:

        writer = csv.writer(f)

        writer.writerow([
            "zone",
            "key_name",
            "algorithm",
            "secret"
        ])

        writer.writerow([
            zone,
            tsig.get("name"),
            tsig.get("algorithm"),
            tsig.get("secret")
        ])

    print(f"Created {filename}")


def write_masters(zone, masters):

    if not masters:
        return

    filename = f"{zone}_zone_secondary_masters.csv"

    with open(filename, "w", newline="") as f:

        writer = csv.writer(f)

        writer.writerow([
            "zone",
            "master_server"
        ])

        for m in masters:
            writer.writerow([zone, m])

    print(f"Created {filename}")


# -------------------------
# PROCESS ZONE
# -------------------------

def process_zone(zone):

    print(f"Processing {zone}")

    zone_info = get_zone_info(zone)

    if not zone_info:
        return

    zone_type = zone_info.get("type", "UNKNOWN")

    print(f"{zone} type: {zone_type}")

    records = fetch_records(zone)

    write_records(zone, records, zone_type)

    # Only perform these for SECONDARY zones
    if zone_type == "SECONDARY":

        masters = zone_info.get("masters", [])

        tsig = get_tsig_key(zone)

        write_masters(zone, masters)

        write_tsig(zone, tsig)


# -------------------------
# MAIN
# -------------------------

with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:

    executor.map(process_zone, zones)