# Akamai Edge DNS Automated Batch Record Management

An automation utility built in Python to safely execute bulk record modifications (such as Sectigo or ACME validation strings) across extensive Akamai Edge DNS zone architectures.

This utility interfaces with the **Akamai Edge DNS Zone Management API (v2)**. It features a strict **Two-Phase Lifecycle Gate** to scan configurations and produce an audit trail prior to modifying live productions. It gracefully appends new records into existing `rdata` structures without overwriting pre-existing TXT strings.

## Features

- **Pre-flight Synchronization:** Pulls your account's master zone registry to catch typos or access alignment errors before hitting Akamai endpoints.
- **Data Protection:** Implements atomic read-before-write merging to append entries to existing TXT record arrays safely.
- **Automated Deployments:** Leverages Akamai v2 native architecture, triggering zone activations automatically upon database updates.
- **B2B Identity Support:** Native support for `.edgerc` profiles, cryptographic request signing (`EdgeGridAuth`), and Multi-Tenant `accountSwitchKey` parameters.

---

## Prerequisites & Installation

### 1. Library Installation
Ensure you install Akamai’s official Python signature integration alongside the necessary runtime environments:

```bash
pip install akamai-edgegrid requests
2. Akamai Credentials Setup
The script reads API authorization tokens directly from your machine's hidden profile storage. Create or append a file named ~/.edgerc containing your API keys:

Ini, TOML
[default]
client_secret = xxxxXXXXxxxxXXXXxxxxXXXXxxxxXXXXxxxxXXXXxxx=
host = akab-xxxx-xxxx-xxxx.luna.akamaiapis.net
access_token = akab-xxxx-xxxx-xxxx-xxxx
client_token = akab-xxxx-xxxx-xxxx-xxxx
File Configurations
Before running the application, make sure the variables inside the configuration block at the top of the script match your requirements:

ACCOUNT_SWITCH_KEY: The target administrative string used to toggle access to the specific account contract.

INPUT_CSV_PATH: Path to your source data file (defaults to zones.csv).

Input Format (zones.csv)
Create a source input spreadsheet containing the literal column headers zone, record_name, and record_value.

Code snippet
zone,record_name,record_value
example.net,_validation-name.example.net,"sectigo.com; accounturi=acct:5555555555@sectigo.com"

Note: The script automatically validates bounding double-quotes ("...") for TXT schema compatibility required by Akamai networks.

Execution Lifecycle
Run the automation tool directly via terminal context:

Bash
python akamai_edns_records.py
Phase 1: Pre-flight Audit Scan
Caching Access Mapping: The tool requests all authoritative entries bound to your accountSwitchKey using showAll=true to cleanly bypass API pagination limits.

Analysis Processing: It steps through each line of your input CSV, evaluating if the zone exists, checking if target record blocks are present, and detecting if values already exist.

Change Log Export: The tool outputs a local tracking log spreadsheet named dns_changes_report.csv. This provides a complete preview of actions (CREATE, UPDATE, or NO_CHANGE) along with Current vs Proposed values.

The Gatekeeper Confirmation
The script pauses execution and waits for validation input:

Plaintext
PLAN PROPOSAL METRICS SUMMARY:
 - Records to Create: 1
 - Records to Append Data Into (Update): 0
 - Records matched perfectly (Will Skip): 0
========================================
💡 Action required: Please open 'dns_changes_report.csv' and audit the plan details.

Do you want to proceed with executing these changes across Akamai networks? (yes/no):
Phase 2: Live Deployment Commit
Type no to terminate safely. No live modifications will be pushed to the edge network.

Type yes to execute the plan. The script processes the record updates via PUT/POST operations. Because of Akamai's native v2 pipeline architecture, committing these updates automatically handles fast-activation. Your zones will briefly transition into a Pending state in the Akamai Control Center UI as they propagate globally across edge servers.

Error Handling & Reliability
HTTP 404 Intercepts: Handled natively to differentiate between completely missing records (triggering CREATE) and API availability errors.

Isolation Boundaries: If a specific zone throws an access denial error (HTTP 403) or validation failure (HTTP 400), the script logs the exact server message to the console, tracks it as a failure, and continues to process the remaining zones without interrupting the queue.

