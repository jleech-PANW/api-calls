import requests, json, configparser, csv
config = configparser.ConfigParser()
config.read(r'')
login_url = config.get('prismacloud', 'cspm_api_url')
 
# Generate API token
def auth_func():
    username = config.get('prismacloud', 'username')
    password = config.get('prismacloud', 'password')
    print("Logging In...")
    try:
        url = f'{login_url}/login'
        payload = f"{{\n  \"password\": \"{password}\",\n  \"username\": \"{username}\"\n}}"
        headers = {
            'Content-Type': 'application/json; charset=UTF-8',
            'Accept': 'application/json; charset=UTF-8'
        }
        response = requests.request("POST", url, headers=headers, data=payload)
        response_json = response.json()
        if 'token' in response_json:
            print("Login Successful")
            return response_json['token']
        else:
            print("Failed to get authentication token")
            return None
 
    except Exception as e:
        print(f"Failed to get authentication token: {e}")
        return None  
 
#Get list of accounts
def acc_list():
    token = auth_func()
    base_url = config.get('prismacloud', 'cspm_api_url')
    url = f'{base_url}/cloud'
    payload = {}
    headers = {
        'Accept': 'application/json;charset=UTF-8',
        'x-redlock-auth': token
    }
    response = requests.request("GET", url, headers=headers, data=payload)
    data = response.json()
 
    account_ids = []
 
    for entry in data:
        account_id = entry.get("accountId")
        if account_id:
            account_ids.append(account_id)
 
        if entry.get("numberOfChildAccounts", 0) > 0:
            cloud_type = entry.get("cloudType", "")
            parent_id = entry.get("accountId", "")
            child_url = f'{base_url}/cloud/{cloud_type}/{parent_id}/project'
            child_response = requests.get(child_url, headers=headers)
            if child_response.status_code == 200:
                child_data = child_response.json()
                for child in child_data:
                    child_id = child.get("accountId")
                    if child_id:
                        account_ids.append(child_id)
    set_account_ids = set(account_ids)
    #print(account_ids)
    return set_account_ids
 
def main():
    cspm_account_ids = acc_list()
    #cspm_account_ids = ["6b34051d-b682-4057-b360-430b628e1b50"]
    base_url = config.get('prismacloud', 'cspm_api_url')
    payload = {}
    token = auth_func()
    headers = {
      'Accept': 'application/json',
      'x-redlock-auth': token
    }
    csv_filename = "prisma_cloud_account_summary.csv"
    fieldnames = ["account", "name", "status", "message", "remediation"]
    a_count = 0
    with open(csv_filename, mode='w', newline='') as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
 
        for account in cspm_account_ids:
            url = f'{base_url}/account/{account}/config/status'
            response = requests.get(url, headers=headers)
            try:
                a_count += 1
                if a_count % 100 == 0:
                    token = auth_func()
                data = response.json()
            except json.JSONDecodeError:
                print(f"Failed to decode JSON for account {account}")
                continue
 
            for entry in data:
                writer.writerow({
                    "account": account,
                    "name": entry.get("name", ""),
                    "status": entry.get("status", ""),
                    "message": entry.get("message", "").strip(),
                    "remediation": entry.get("remediation", "").strip()
                })
 
main()
