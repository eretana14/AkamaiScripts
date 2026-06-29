Akamai SiteShield Property Audit Tool
This script automates the discovery of properties utilizing a specific SiteShield Map. It searches your account across all active and expired contracts, retrieves the necessary configuration and rule tree details using the Property Manager API (PAPI), and compiles a CSV report.

************* Prerequisites *************

1. Python Environment
You must have Python 3.x installed. You will also need the akamai-edgegrid library to handle API authentication.

Install dependencies: `pip install akamai-edgegrid requests`

2. Akamai API Credentials
You need an .edgerc file containing your API credentials.

Required API Permissions: Your API client must have "Read" access to the Property Manager API (PAPI).

File Location: By default, the script looks for this file at `~/.edgerc` (your user home directory) under the `[default]` section.

************* Configuration *************

Before running the script, open the Python script and update the Configuration section:

# Manually specify the SiteShield Map ID you want to track here.

### Add it to the TARGET_MAP_ID variable inside the script.

`TARGET_MAP_ID = "s470.akamaiedge.net"`

### Account Switch Key (If Applicable)
If you manage multiple accounts or need to query a specific sub-account, provide the account switch key here. Leave as `""` if not needed.

`ACCOUNT_SWITCH_KEY = "F-AC-1889191:1-2RBL"`

### Hidden Contracts (Optional)
Add any completely hidden/legacy contracts that the API scrubbed but you still want to explicitly scan. Ensure you use the `ctr_` prefix.

`FORCE_SCAN_CONTRACTS = ["ctr_P-39PY5AF"]`

************* Usage *************

Run the script from your terminal:

`python SiteShieldDiscovery.py`

************* Output *************

The script prints its progress to the console and generates a CSV file named `properties_using_siteshield.csv` in the same directory. This file contains:
* Property Name
* Property ID
* Contract ID
* Group ID
* Version Checked
* Network Status (Active Production, Active Staging, or Inactive Draft)