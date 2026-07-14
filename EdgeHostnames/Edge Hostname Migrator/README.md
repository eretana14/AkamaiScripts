# Akamai Dual-Stack (IPv4 to IPv6) Edge Hostname Migrator

This script automates the discovery and migration of Akamai Edge Hostnames from IPv4-only to Dual-Stack (IPv4 + IPv6). It utilizes a safe, two-phase approach: discovering legacy hostnames across all account groups and contracts, and safely applying targeted updates via the Edge Hostnames API without requiring full property configuration deployments.

************* Prerequisites *************

1. Python Environment 
You must have Python 3.x installed. You will also need the edgegrid-python library to handle API authentication.

Install dependencies: `pip install edgegrid-python requests urllib3`

2. Akamai API Credentials 
You need an .edgerc file containing your API credentials.

Required API Permissions: Your API client must have "Read" access to the Property Manager API (PAPI) and "Read/Write" access to the Edge Hostnames API (HAPI).

File Location: By default, the script looks for this file at `~/.edgerc` (your user home directory) under the `[default]` section.

************* Configuration ************* 

Before running the script, open `edgehostname_editor.py` and update the Configuration section:

## Manually specify your Account Switch Key here (e.g., "1-ABC12").

## Leave it as an empty string "" if you want to use the default account access.

```python
ACCOUNT_SWITCH_KEY = "1-6JHGX:1-8BYUX"
```

************* Usage *************

**Phase 1: Discovery**
Run the script without arguments to scan your account architecture and identify hostnames restricted to IPv4.
```bash
python edgehostname_editor.py
```
*This generates an actionable file named `discovered_ipv4_hostnames.csv`.*

**Phase 2: Bulk Update Migration**
Review the generated CSV. Once verified, execute Phase 2 to patch the selected edge hostnames to `IPV6_IPV4_DUALSTACK`.
```bash
python edgehostname_editor.py --phase2
```