Akamai CPS ACME Challenge Retriever
This script automates the retrieval of DNS-01 (TXT) validation records for Let's Encrypt DV SAN certificates managed via Akamai's Certificate Provisioning System (CPS). It eliminates the manual effort of copy-pasting dozens of SAN tokens from the UI.

************ Prerequisites ************
1. Python Environment
You must have Python 3.x installed. You will also need the akamai-edgegrid library to handle API authentication.

Install dependencies:
pip install akamai-edgegrid requests

2. Akamai API Credentials
You need an .edgerc file containing your API credentials.

Create Credentials: Follow the Akamai: Get Started with APIs guide: https://techdocs.akamai.com/developer/docs/edgegrid

Required API Permissions: Your API client must have "Read/Write" (or at least Read) access to the CPS (Certificate Provisioning System) API.

File Location: By default, the script looks for this file at ~/.edgerc (your user home directory).

3. Identify Your Certificate
You do not need to hunt for IDs. You only need one of the following from the Akamai Control Center:

Common Name: The primary domain of the certificate (e.g., www.example.com).

Slot Number: The specific CPS slot ID (found in the "Slot" column in the CPS dashboard).


************ Configuration ************
Before running the script, open get_dv_dns_tokens.py and update the Search Criteria section:
# Update these to match the certificate you are validating
SEARCH_COMMON_NAME = "yourdomain.com" 
SEARCH_SLOT = None # Set to your slot number if common name is not unique


************ Instructions to Run ************
Step 1: Initialize the Change
Ensure your certificate is in the "Awaiting User Input" or "Awaiting DNS" state in Akamai Control Center. If the change has not been started yet, this script will find no pending tokens.

Step 2: Execute the Script
Run the script from your terminal:
python get_dv_dns_tokens.py

Step 3: Process the Output
The script will generate a file named akamai_dns_challenges.csv in the same directory. This file contains:

Record Name: (e.g., _acme-challenge.example.com)

TTL: (Standard 60 seconds)

Type: TXT

Value: The unique ACME token.

