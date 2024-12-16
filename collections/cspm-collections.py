import requests, json, configparser, openpyxl
from collections import defaultdict

# Authenticate with the prisma tenant and retreive a token
def auth_func():
    config = configparser.ConfigParser()
    config.read('config.ini')
    login_url = config.get('prismacloud', 'cspm_api_url')
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
def get_accounts():
    print("Getting onboarded accounts.")
    token = auth_func()
    config = configparser.ConfigParser()
    config.read('config.ini')
    api_url = config.get('prismacloud', 'cspm_api_url')
    url = f"{api_url}/cloud"
    payload = {}
    headers = {
      'Accept': 'application/json',
      'x-redlock-auth': token
    }
    response = requests.request("GET", url, headers=headers, data=payload)
    global onboarded_accounts
    onboarded_accounts = [(item.get("accountId", "")) for item in response.json()]
    
    
# Get a list of existing prisma collections
def get_collections():
    print("Getting current collections.")
    token = auth_func()
    config = configparser.ConfigParser()
    config.read('config.ini')
    api_url = config.get('prismacloud', 'cspm_api_url')
    url = f"{api_url}/entitlement/api/v1/collection?page_size=500"
    payload = {}
    headers = {
      'Accept': 'application/json',
      'x-redlock-auth': token
    }
    response = requests.request("GET", url, headers=headers, data=payload)
    json_response = json.loads(response.text)
    global collections_data
    collections_data = json_response["value"]
    global collection_list
    collection_list = []
    for collection in collections_data:
      collection_list.append(collection["name"])
#     print(collection_list)

# Parse the FinOps excel for Business Units and their associated Account IDs
def get_BUs():
    print("Getting Business Units.")
    file_path = 'FinOps_Hyperscalers_account_2024-11-25.xlsx'
    wb = openpyxl.load_workbook(file_path)
    sheet = wb.active
    result_dict = defaultdict(list)
    for row in sheet.iter_rows(min_row=2):
        business_unit = row[7].value
        account = row[10].value 
        if business_unit:
            #Reformat Business Unit names to make them more friendly to URL requests
            business_unit = business_unit.replace("_bu:_value_not_provided","No_Business_Unit")
            business_unit = business_unit.replace(" ", "_")
            if account:
                result_dict[business_unit].append(account)
    global json_objects
    json_objects = [
        {"name": f"FinOps_{business_unit}", "assetGroups": { "accountIds": accounts }}
        for business_unit, accounts in result_dict.items()
    ]
    removed_accounts = []
    for obj in json_objects:
        if "assetGroups" in obj and "accountIds" in obj["assetGroups"]:
            all_accounts = obj["assetGroups"]["accountIds"]
            valid = [account for account in all_accounts if account in onboarded_accounts]
            invalid = [account for account in all_accounts if account not in onboarded_accounts]
            obj["assetGroups"]["accountIds"] = valid
            if invalid:
                removed_accounts.append({
                    "name": obj["name"],
                    "missingAccounts": invalid
                })
    outfile_accounts = open("nononboarded_accounts.txt", "w")
    outfile_accounts.write(json.dumps(removed_accounts, indent=4))
    outfile_accounts.close
    print("Created nononboarded_accounts.txt")

    global business_list
    business_list = []
    for bu_obj in json_objects:
        bu_name = bu_obj["name"]
        business_list.append(bu_name)
#   print(business_list)

# Create a list of Missing collections, this will represent new Business Units added. Create a list of Existing collections. 
# Later we will use missing_collections to create new collections and existing_collections will be used to update existing collections as these use the slightly different endpoints
 
def compare_collections():
    global missing_collections
    global existing_collections
    missing_collections = list(set(business_list) - set(collection_list))
    existing_collections = list(set(business_list) & set(collection_list))

# Loop through existing_collection list and compare to the FinOps excel data. Update matching items.
def update_collections():
    print("Updateing Existing Collections.")
    token = auth_func()
    config = configparser.ConfigParser()
    config.read('config.ini')
    api_url = config.get('prismacloud', 'cspm_api_url')
    for existing_collection in existing_collections:
        for obj in json_objects:
            if existing_collection in obj["name"]:
                for colection_item in collections_data:
                    if obj["name"] in colection_item["name"]:
                        col_id = colection_item["id"]
                print(f"Updating {existing_collection}")
                url = f"{api_url}/entitlement/api/v1/collection/{col_id}"
                payload = json.dumps(obj)
                #print(payload)
                headers = {
                    'Content-Type': 'application/json',
                    'x-redlock-auth': token
                }
                response = requests.request("PUT", url, headers=headers, data=payload)
                print(response.status_code)

#Loop through missing_collections list and compare to FinOps excel data. Create matching items.
def create_collections():
    print("Creating Missing Collections.")
    token = auth_func()
    config = configparser.ConfigParser()
    config.read('config.ini')
    api_url = config.get('prismacloud', 'cspm_api_url')
    for missing_collection in missing_collections:
        for obj in json_objects:
            if missing_collection in obj["name"]:
                print(f"Creating {missing_collection}")
                url = f"{api_url}/entitlement/api/v1/collection"
                payload = json.dumps(obj)
                #print(payload)
                headers = {
                    'Content-Type': 'application/json',
                    'x-redlock-auth': token
                }
                response = requests.request("POST", url, headers=headers, data=payload)
                print(response.status_code)


# Create Data
get_accounts()
get_collections()
get_BUs()
compare_collections()

# Use Data
if existing_collections:
    update_collections()
else:
    print("No Existing Collections")

if missing_collections:
    create_collections()
else:
    print("No Missing Collections")
