Akamai Secure By Default (SBD) Hostname Auditor
This script automates the audit of an Akamai CDN account to verify and identify how many hostnames are currently using Secure By Default (SBD) certificates. It handles API pagination, merges cross-environment deployments, and eliminates the manual effort of scraping individual property configurations from the Control Center UI.

************ Prerequisites ************

1. Python Environment
You must have Python 3.x installed. You will also need the edgegrid-python library to handle API authentication, requests for handling networking, and openpyxl for Excel generation.

Install dependencies:
pip install edgegrid-python requests openpyxl

2. Akamai API Credentials
You need an .edgerc file containing your API credentials.

Create Credentials: Follow the Akamai: Get Started with APIs guide: https://techdocs.akamai.com/developer/docs/edgegrid

Required API Permissions: Your API client must have "Read" access to the PAPI (Property Manager API).

File Location: By default, the script looks for this file at ~/.edgerc (your user home directory).

3. Identify Your Account Context
If you are managing multiple accounts or a hierarchical client tenant structure, ensure you have the required Account Switch Key. This key allows the script to explicitly query the correct corporate profile context.


************ Configuration ************

Before running the script, open akamai_sbd_only_audit.py and update the Configuration Variables section:

# Update these to match your environment and account context
EDGERC_PATH = "~/.edgerc"
EDGERC_SECTION = "default"
ACCOUNT_SWITCH_KEY = "1-IV63:1-2RBL"  # Set to None if account context switching is not required
OUTPUT_FILENAME = "akamai_sbd_hostnames.xlsx"


************ Instructions to Run ************

Run the script from your terminal:
python akamai_sbd_only_audit.py

The script will log execution milestones directly to the terminal console and automatically generate an executive-ready, color-coded Excel spreadsheet matching your configurations.