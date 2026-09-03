"""Verify that VS Code/Python can authenticate to Azure without storing secrets."""
import json
import os
import subprocess
from azure.identity import DefaultAzureCredential


def run_az(*args):
    try:
        return subprocess.check_output(["az", *args], text=True, stderr=subprocess.STDOUT)
    except FileNotFoundError:
        raise SystemExit("Azure CLI is not installed or not on PATH. Install it, restart VS Code, then run: az login")
    except subprocess.CalledProcessError as exc:
        raise SystemExit(f"Azure CLI command failed:\n{exc.output}")


def main():
    print("1) Checking Azure CLI login...")
    current = json.loads(run_az("account", "show", "--output", "json"))
    print(f"   Signed in subscription: {current.get('name')} ({current.get('id')})")

    print("2) Checking Azure SDK token acquisition...")
    credential = DefaultAzureCredential(exclude_interactive_browser_credential=False)
    token = credential.get_token("https://management.azure.com/.default")
    print(f"   Management token acquired successfully. Expires on epoch: {token.expires_on}")

    print("3) Listing subscriptions visible to this Azure CLI identity...")
    subscriptions = json.loads(run_az("account", "list", "--output", "json"))
    if not subscriptions:
        raise SystemExit("Login succeeded, but no Azure subscription is visible to this account.")
    for sub in subscriptions:
        print(f"   - {sub.get('name')}: {sub.get('id')}")

    expected = os.getenv("AZURE_SUBSCRIPTION_ID")
    if expected and expected != "00000000-0000-0000-0000-000000000000":
        found = any(s.get("id") == expected for s in subscriptions)
        print(f"4) Subscription from .env visible: {found}")
        if not found:
            raise SystemExit("The AZURE_SUBSCRIPTION_ID in .env is not visible to the current Azure login.")

    print("\nSUCCESS: Azure CLI and Azure SDK authentication are working.")


if __name__ == "__main__":
    main()
