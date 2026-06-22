Akamai AppSec Hostname Onboarding Script This script automates the mass onboarding of hostnames into an Akamai Application Security (AppSec) Configuration and maps them to a specific Security Policy via Website Match Targets. It eliminates the manual effort of adding and mapping individual hostnames inside the Akamai Control Center UI when dealing with large onboarding scopes.

************ Prerequisites ************

  1. Python Environment You must have Python 3.x installed. You will also need the akamai-edgegrid and requests libraries to handle API authentication and requests.

Install dependencies: pip install edgegrid-python requests

  2. Akamai API Credentials You need an .edgerc file containing your API credentials.

Required API Permissions: Your API client credentials must have "Read/Write" access to the Application Security API (AppSec API).

File Location: By default, the script looks for this file at ~/.edgerc (your user home directory) under the [default] section.

************ Configuration ************ Before running the script, open sec_hostnames_onboard.py and update the Configuration section:

Manually specify your variables here (e.g., Config ID, Policy ID, and Account Switch Key).

Leave the Account Switch Key as an empty string "" if you want to use the default account access.

CONFIG_ID = 100757
POLICY_ID = "1234_255276"
ACCOUNT_SWITCH_KEY = "B-M-1YX7F48:1-8BYUX"
CSV_FILE_PATH = "hostnames.csv"

************ Instructions to Run ************ Step 1: Prepare your Input File Create a file named hostnames.csv in the same directory as the script. Ensure it contains a 'hostname' header row followed by your list of domains to onboard.

Step 2: Update Configuration Constants Ensure you have inserted the appropriate configuration values (CONFIG_ID, POLICY_ID, and ACCOUNT_SWITCH_KEY) inside the script variables matching your target environment.

Step 3: Execute the Script Run the script from your terminal: python sec_hostnames_onboard.py

Step 4: Review the Results The script will clone your latest configuration version, append your CSV hostnames to the root layer, and map them to your specified security policy target list. Review the freshly prepared draft version in the Akamai Control Center before deploying to Staging/Production.