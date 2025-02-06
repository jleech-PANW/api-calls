import requests, json, configparser, openpyxl
from tabulate import tabulate

config = configparser.ConfigParser()
config.read('config.ini')
cspm_url = config.get('prismacloud', 'cspm_api_url')
cwp_url = config.get('prismacloud', 'cwp_api_url')


def auth_func():
    login_url = cspm_url
    username = config.get('prismacloud', 'username')
    password = config.get('prismacloud', 'password')
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
            print("Retrieved Token")
            return response_json['token']
        else:
            print("Failed to get authentication token")
            return None 
    except Exception as e:
        print(f"Failed to get authentication token: {e}")
        return None    

def cspm_tags():
    token = auth_func()
    url = f'{cspm_url}/search/api/v2/config'
    headers = {
      'Content-Type': 'application/json',
      'x-redlock-auth': token
    }
    rql = "config from cloud.resource where api.name = 'aws-lambda-list-functions' AND json.rule = tags[*].key contains \"owner_team\""
    in_data = {
        "query": rql,
        "limit": 100,
        "timeRange": {
            "relativeTimeType": "BACKWARD",
            "type": "relative",
            "value": {
                "amount": 24,
                "unit": "hour"
            }
        },
        "withResourceJson": True
    }
    payload = json.dumps(in_data)   
    response = requests.request("POST", url, headers=headers, data=payload)
    data_out = json.loads(response.text)    
#    print(response.status_code)
#    print(response.text)

    rows = []
    for item in data_out.get("items", []):
        owner_team = "N/A"
        tags = item.get("data", {}).get("tags", [])
        for tag in tags:
            if tag.get("key") == "owner_team":
                owner_team = tag.get("value")
                break
        
        rows.append([
            item.get("id", "N/A"),
            item.get("accountId", "N/A"),
            item.get("cloudType", "N/A"),
            item.get("resourceType", "N/A"),
            owner_team
        ])

    # Print table
    headers = ["ID", "Account ID", "Cloud Type", "Resource Type", "Owner Team"]
    print(tabulate(rows, headers=headers, tablefmt="grid"))


cspm_tags()
