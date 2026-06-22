Akamai Unused Edge Hostnames Finder
This script automates the identification and collection of Akamai Edge Hostnames that are completely detached from any active Property Manager configurations. It eliminates the manual effort of auditing individual delivery configurations to find orphan hostnames across your account groups.

************ Prerequisites ************
1. Python Environment
You must have Python 3.x installed. You will also need the akamai-edgegrid library to handle API authentication.

Install dependencies:
pip install akamai-edgegrid requests

2. Akamai API Credentials
You need an .edgerc file containing your API credentials.

Required API Permissions: Your API client must have "Read" (or Read/Write) access to the Property Manager API (PAPI).

File Location: By default, the script looks for this file at ~/.edgerc (your user home directory) under the [default] section.


************ Configuration ************
Before running the script, open find_unused_edge_hostnames.py and update the Configuration section:

# Manually specify your Account Switch Key here (e.g., "1-ABC12"). 
# Leave it as an empty string "" if you want to use the default account access.
ACCOUNT_SWITCH_KEY = "YOUR_ACCOUNT_SWITCH_KEY_HERE"


************ Instructions to Run ************
Step 1: Update your Account Switch Key
Ensure you have inserted the appropriate key into the ACCOUNT_SWITCH_KEY variable if you are managing a sub-account, or verified it is blank for default access.

Step 2: Execute the Script
Run the script from your terminal:
python unused_edgehostnames.py

Step 3: Review the Results
The script will output a clean console log tracking its progress through your groups. Once finished, a new file named unused_edge_hostnames_YYYYMMDD_HHMM.csv will appear in your working directory containing all discovered orphaned records.