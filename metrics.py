import requests
import csv
import json

# The user is expected to have an 'auth/panw.py' file in the same directory
# or in the Python path, containing the auth_func() function.
try:
    from panw import auth_func
except ImportError:
    print("Error: Could not import 'auth_func' from 'auth.panw'.")
    print("Please ensure the authentication script is in the correct path.")
    exit(1)

def get_vulnerability_overview(cspm_url: str, headers: dict) -> dict:
    """
    Fetches total and unique vulnerability counts from the overview endpoint.

    Args:
        cspm_url: The base URL for the Prisma Cloud instance.
        headers: The authentication headers for the API request.

    Returns:
        A dictionary containing the API response JSON, or an empty dict on failure.
    """
    # This endpoint URL is based on v4 as seen in the HAR file
    overview_url = f"{cspm_url}/uve/api/v4/dashboard/vulnerabilities/overview"
    
    # This payload is based on the HAR file
    payload = {
        "assetTypes": ["package", "iac", "registryImage", "vmImage", "deployedImage", "serverlessFunction", "host"],
        "lifeCycle": ["code", "build", "deploy", "run"],
        "severities": ["critical", "high", "medium", "low"],
        "accountGroups": [],
        "accountIds": []
    }
    
    print("Fetching vulnerability overview data...")
    try:
        response = requests.post(overview_url, headers=headers, json=payload)
        response.raise_for_status()  # Raises an exception for 4xx or 5xx status codes
        print("Successfully fetched overview data.")
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching vulnerability overview: {e}")
        return {}

def get_vulnerable_assets(cspm_url: str, headers: dict) -> dict:
    """
    Fetches vulnerability counts for specific asset types.

    Args:
        cspm_url: The base URL for the Prisma Cloud instance.
        headers: The authentication headers for the API request.

    Returns:
        A dictionary containing the API response JSON, or an empty dict on failure.
    """
    # This endpoint URL is based on v2 as seen in the HAR file
    assets_url = f"{cspm_url}/uve/api/v2/dashboard/vulnerabilities/vulnerableAsset"
    
    # This payload is based on the HAR file, but modified to include "low" severity
    # to ensure all vulnerability levels are captured for the report.
    payload = {
        "lifeCycle": ["code", "build", "deploy", "run"],
        "assetTypes": ["deployedImage", "serverlessFunction", "host", "registryImage"],
        "severities": ["critical", "high", "medium", "low"],
        "accountGroups": [],
        "accountIds": []
    }
    
    print("Fetching vulnerable asset data...")
    try:
        response = requests.post(assets_url, headers=headers, json=payload)
        response.raise_for_status()
        print("Successfully fetched vulnerable asset data.")
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching vulnerable asset data: {e}")
        return {}

# --- MODIFIED FUNCTION ---
def get_unique_vulns_by_asset(cspm_url: str, headers: dict) -> dict:
    """
    Fetches unique vulnerability (CVE) counts per asset type and severity
    using the /uve/api/v1/vulnerabilities/search RQL endpoint.

    Args:
        cspm_url: The base URL for the Prisma Cloud instance.
        headers: The authentication headers for the API request.

    Returns:
        A dictionary with the aggregated unique counts.
    """
    
    # --- MODIFIED ---
    # This endpoint and payload format are based on the user's corrections 
    # and the provided HAR file [cite: 485, 500]
    search_url = f"{cspm_url}/uve/api/v1/vulnerabilities/search"
    
    # --- MODIFIED ---
    # Asset type strings as specified by the user.
    # We map internal keys (used by process_metrics) to the RQL query strings.
    asset_types_map = {
        "host": "Host",
        "registryImage": "Container Registry Image",
        "deployedImage": "Deployed Image",
        "serverlessFunction": "Serverless Function",
    }
    severities = ["critical", "high", "medium", "low"]
    
    # This will store the final counts, e.g., {"host": {"critical": 10, ...}}
    unique_metrics = {}

    print("Fetching unique vulnerability data by asset type (this may take a moment)...")
    
    # Loop through the map to keep internal keys consistent for process_metrics
    for internal_key, rql_asset_name in asset_types_map.items():
        unique_metrics[internal_key] = {}
        print(f"  Querying for asset type: {rql_asset_name}")
        for sev in severities:
            
            # --- MODIFIED ---
            # Construct the RQL query string payload [cite: 500]
            rql_query = f"vulnerability where asset.type = '{rql_asset_name}' AND severity = '{sev}'"
            payload = {"query": rql_query}
            
            try:
                response = requests.post(search_url, headers=headers, json=payload)
                response.raise_for_status()
                
                # --- MODIFIED ---
                # Parse the response to find "data" -> "totalRows" as specified 
                response_json = response.json()
                count = response_json.get("data", {}).get("totalRows", 0)
                
                unique_metrics[internal_key][sev] = count
                
            except requests.exceptions.RequestException as e:
                print(f"    Error fetching unique data for {rql_asset_name}/{sev}: {e}")
                unique_metrics[internal_key][sev] = 0
                
    print("Successfully fetched unique vulnerability data by asset.")
    return unique_metrics

def process_metrics(overview_data: dict, assets_data: dict, unique_asset_data: dict) -> dict:
    """
    Processes the raw API data and aggregates it into a structured dictionary.

    Args:
        overview_data: The JSON response from the overview endpoint.
        assets_data: The JSON response from the vulnerable assets endpoint.
        unique_asset_data: The JSON response from the unique vulnerabilities endpoint.

    Returns:
        A dictionary with aggregated metrics.
    """
    metrics = {
        "Total Vulnerabilities": {},
        "Unique Vulnerabilities": {},
        "Hosts with Vulnerabilities": {"critical": 0, "high": 0, "medium": 0, "low": 0},
        "Containers with Vulnerabilities": {"critical": 0, "high": 0, "medium": 0, "low": 0},
        "Images with Vulnerabilities": {"critical": 0, "high": 0, "medium": 0, "low": 0},
        "Functions with Vulnerabilities": {"critical": 0, "high": 0, "medium": 0, "low": 0},
        # --- NEW METRICS ---
        "Unique Host Vulnerabilities": {},
        "Unique Container Vulnerabilities": {},
        "Unique Image Vulnerabilities": {},
        "Unique Function Vulnerabilities": {},
    }
    
    # Process overview data
    if overview_data.get("overviewSummary"):
        summary = overview_data["overviewSummary"]
        if summary.get("totalVulnerabilities"):
            vulns = summary["totalVulnerabilities"]
            metrics["Total Vulnerabilities"] = {
                "critical": vulns.get("criticalCount", 0),
                "high": vulns.get("highCount", 0),
                "medium": vulns.get("mediumCount", 0),
                "low": vulns.get("lowCount", 0),
            }
        if summary.get("totalUniqueCves"):
            cves = summary["totalUniqueCves"]
            metrics["Unique Vulnerabilities"] = {
                "critical": cves.get("criticalCount", 0),
                "high": cves.get("highCount", 0),
                "medium": cves.get("mediumCount", 0),
                "low": cves.get("lowCount", 0),
            }

    # Process asset data
    asset_mapping = {
        "host": "Hosts with Vulnerabilities",
        "deployedImage": "Containers with Vulnerabilities",
        "registryImage": "Images with Vulnerabilities",
        "serverlessFunction": "Functions with Vulnerabilities",
    }
    
    if assets_data.get("value"):
        for asset_group in assets_data["value"]:
            asset_type = asset_group.get("assetType")
            metric_name = asset_mapping.get(asset_type)
            if not metric_name:
                continue
            
            # Aggregate counts from all providers/stats within an asset type
            for stat in asset_group.get("stats", []):
                vulns = stat.get("vulnerabilities", {})
                metrics[metric_name]["critical"] += vulns.get("criticalCount", 0)
                metrics[metric_name]["high"] += vulns.get("highCount", 0)
                metrics[metric_name]["medium"] += vulns.get("mediumCount", 0)
                metrics[metric_name]["low"] += vulns.get("lowCount", 0)

    # Process unique asset data
    unique_asset_mapping = {
        "host": "Unique Host Vulnerabilities",
        "deployedImage": "Unique Container Vulnerabilities",
        "registryImage": "Unique Image Vulnerabilities",
        "serverlessFunction": "Unique Function Vulnerabilities",
    }
    
    for asset_type, severities in unique_asset_data.items():
        metric_name = unique_asset_mapping.get(asset_type)
        if metric_name:
            # Data is already in the correct format {"critical": X, "high": Y, ...}
            metrics[metric_name] = severities
                
    return metrics

def write_to_csv(metrics: dict, filename="vulnerability_metrics.csv"):
    """
    Writes the processed metrics to a CSV file.

    Args:
        metrics: The dictionary of aggregated metrics.
        filename: The name of the output CSV file.
    """
    print(f"Writing metrics to {filename}...")
    try:
        with open(filename, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            
            # Write header
            header = ['Metric', 'Critical', 'High', 'Medium', 'Low', 'Total']
            writer.writerow(header)
            
            # Define a sort order to keep the CSV organized
            metric_order = [
                "Total Vulnerabilities",
                "Unique Vulnerabilities",
                "---", # Used as a separator, will be skipped
                "Hosts with Vulnerabilities",
                "Unique Host Vulnerabilities",
                "---",
                "Containers with Vulnerabilities",
                "Unique Container Vulnerabilities",
                "---",
                "Images with Vulnerabilities",
                "Unique Image Vulnerabilities",
                "---",
                "Functions with Vulnerabilities",
                "Unique Function Vulnerabilities"
            ]
            
            # Get any metrics that might not be in the sort order (though they should be)
            remaining_metrics = set(metrics.keys()) - set(metric_order)
            
            for metric_name in metric_order + sorted(list(remaining_metrics)):
                if metric_name == "---":
                    writer.writerow([]) # Write a blank line
                    continue

                severities = metrics.get(metric_name)
                if not severities: # Skip empty metrics
                    continue
                
                critical = severities.get("critical", 0)
                high = severities.get("high", 0)
                medium = severities.get("medium", 0)
                low = severities.get("low", 0)
                total = critical + high + medium + low
                
                row = [metric_name, critical, high, medium, low, total]
                writer.writerow(row)
        print("Successfully wrote data to CSV.")
    except IOError as e:
        print(f"Error writing to file: {e}")

def main():
    """Main function to orchestrate the script."""
    # Step 1: Get authentication credentials from external function
    try:
        token, cspm_url, cwp_url = auth_func()
    except Exception as e:
        print(f"An error occurred during authentication: {e}")
        return
        
    if not token or not cspm_url:
        print("Authentication failed. Please check your auth_func implementation.")
        return
        
    headers = {
        "x-redlock-auth": token,
        "Content-Type": "application/json"
    }
    
    # Step 2: Fetch data from APIs
    overview_data = get_vulnerability_overview(cspm_url, headers)
    assets_data = get_vulnerable_assets(cspm_url, headers)
    unique_asset_data = get_unique_vulns_by_asset(cspm_url, headers)
    
    # Step 3: Process the data
    if not overview_data and not assets_data and not unique_asset_data:
        print("Failed to fetch any data. Exiting.")
        return
        
    final_metrics = process_metrics(overview_data, assets_data, unique_asset_data)
    
    # Step 4: Write to CSV
    write_to_csv(final_metrics)

if __name__ == "__main__":
    main()
