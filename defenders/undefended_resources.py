import requests, json, configparser, openpyxl
from openpyxl import load_workbook
def auth_func():
    config = configparser.ConfigParser()
    config.read('config.ini')
    login_url = config.get('prismacloud', 'cspm_api_url')
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


def entity_report():
  print("Creating Entity Report")
  token = auth_func()
  config = configparser.ConfigParser()
  config.read('config.ini')
  base_url = config.get('prismacloud', 'cwp_api_url')
  headers = {
      'Content-Type': 'application/json',
      'x-redlock-auth': token
  }
  payload = {}  
  file_name = "undefended_resources.xlsx"
  url = f'{base_url}/api/v33.01/cloud/discovery/entities?defended=false&offset=0'
  response = requests.request("GET", url, headers=headers, data=payload)
  print(f"Initial response Code: {response.status_code}")
  data = json.loads(response.text)
  wb = openpyxl.Workbook()
  ws = wb.active
  ws.title = "Undefended Resources"
  wb_headers = ["Name", "ARN", "AccountID", "Region"]
  ws.append(wb_headers)
  offset = 0
  for item in data:
    ws.append([item.get('name', ''), item.get('arn', ''), item.get('accountID', ''), item.get('region', '')])
  
  while data is not None:
    offset += 50
    url = f'{base_url}/api/v33.01/cloud/discovery/entities?defended=false&offset={offset}'
    response = requests.request("GET", url, headers=headers, data=payload)
    try:
      data = json.loads(response.text)
    except json.JSONDecodeError:
       wb.save(file_name)
       print("Entity Run Complete")
       return
    if data is None:
      wb.save(file_name)
      print("Entity Run Complete")
      return
    for item in data:
      ws.append([item.get('name', ''), item.get('arn', ''), item.get('accountID', ''), item.get('region', '')])
    wb.save(file_name)
    print(f"Saved up to {offset}. Response Code: {response.status_code}")
    if offset % 1000 == 0: 
      token = auth_func()

def vm_report():
  print("Creating VM Report")
  token = auth_func()
  config = configparser.ConfigParser()
  config.read('config.ini')
  base_url = config.get('prismacloud', 'cwp_api_url')
  headers = {
      'Content-Type': 'application/json',
      'x-redlock-auth': token
  }
  payload = {}  
  file_name = "undefended_resources.xlsx"
  url = f'{base_url}/api/v33.01/cloud/discovery/vms?offset=0&hasDefender=false'
  response = requests.request("GET", url, headers=headers, data=payload)
  print(f"Initial response Code: {response.status_code}")
  data = json.loads(response.text)
  wb = load_workbook(file_name)
  ws2 = wb.create_sheet(title="VMs")
  wb_headers = ["Name", "ARN", "AccountID", "Region"]
  ws2.append(wb_headers)
  offset = 0
  for item in data:
    ws2.append([item.get('name', ''), item.get('arn', ''), item.get('accountID', ''), item.get('region', '')])
  
  while data is not None:
    offset += 50
    url = f'{base_url}/api/v33.01/cloud/discovery/vms?offset={offset}&hasDefender=false'
    response = requests.request("GET", url, headers=headers, data=payload)
    try:
      data = json.loads(response.text)
    except json.JSONDecodeError:
       wb.save(file_name)
       print("VM Run Complete")
       return
    if data is None:
      wb.save(file_name)
      print("VM Run Complete")
      return
    for item in data:
      ws2.append([item.get('name', ''), item.get('arn', ''), item.get('accountID', ''), item.get('region', '')])
    wb.save(file_name)
    print(f"Saved up to {offset}. Response Code: {response.status_code}")
    if offset % 1000 == 0: 
      token = auth_func()
  
  
entity_report()
vm_report()
