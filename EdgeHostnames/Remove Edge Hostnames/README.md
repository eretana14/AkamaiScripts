Akamai Edge Hostnames Remover This script automates the targeted deletion of Akamai Edge Hostnames. It searches your account for specific hostnames, retrieves the necessary DNS Zone and Record details using the Hostname API (HAPI), and performs the deletion. It includes safety features to prevent accidental deletions.

************ Prerequisites ************

1. Python Environment You must have Python 3.x installed. You will also need the akamai-edgegrid library to handle API authentication.

Install dependencies: pip install akamai-edgegrid requests

2. Akamai API Credentials You need an .edgerc file containing your API credentials.

Required API Permissions: Your API client must have "Read" access to the Property Manager API (PAPI) and "Read/Write" access to the Hostname API (HAPI).

File Location: By default, the script looks for this file at ~/.edgerc (your user home directory) under the [terraform] section.

************ Configuration ************ Before running the script, open remove_edge_hostnames.py and update the Configuration section:

# Manually specify the Edge Hostnames you want to remove here.

## Add them to the EDGE_HOSTNAMES_TO_REMOVE list inside the script.

EDGE_HOSTNAMES_TO_REMOVE = [
    "example.com.edgekey.net",
]

# Manually specify your Account Switch Key here (e.g., "1-6JHGX:1-8BYUX").

## Set it to None if you want to use the default account access.

ACCOUNT_SWITCH_KEY = "1-6JHGX:1-8BYUX"

# Manually specify your Contract ID and Group ID here.

CONTRACT_ID = "ctr_1-1NC95D"
GROUP_ID = "grp_243619"

************ Execution ************ Run the script from your terminal:

python remove_edge_hostnames.py