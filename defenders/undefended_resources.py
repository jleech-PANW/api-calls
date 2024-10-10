import requests, json, configparser, openpyxl
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
token = auth_func()
def report():
  config = configparser.ConfigParser()
  config.read('config.ini')
  base_url = config.get('prismacloud', 'cwp_api_url')
  headers = {
      'Content-Type': 'application/json',
      'x-redlock-auth': f'{token}'
  }
  payload = {}
  url = f'{base_url}/api/v33.01/cloud/discovery/entities?defended=false'
  response = requests.request("GET", url, headers=headers, data=payload)
  data = json.loads(response.text)
  wb = openpyxl.Workbook()
  ws = wb.active
  ws.title = "Undefended Resources"
  headers = ["Name", "ARN", "AccountID", "Region"]
  ws.append(headers)
  for item in data:
    ws.append([item.get('name', ''), item.get('arn', ''), item.get('accountID', ''), item.get('region', '')])
  
  file_name = "undefended_resources.xlsx"
  wb.save(file_name)

report()
