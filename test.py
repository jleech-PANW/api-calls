import hvac
import boto3
import requests
import os

# --- CONFIGURATION ---
# Best practice: pass these as environment variables to the Lambda
VAULT_ADDR = os.environ.get('VAULT_ADDR') # e.g., 'https://vault.example.com:8200'
VAULT_ROLE = os.environ.get('VAULT_ROLE') # The role *defined in Vault* for your Lambda
VAULT_NAMESPACE = os.environ.get('VAULT_NAMESPACE') # e.g., 'admin/my-ns'
VAULT_SECRETS_PATH = os.environ.get('VAULT_SECRETS_PATH') # e.g., 'prisma/creds'
VAULT_MOUNT_POINT = os.environ.get('VAULT_MOUNT_POINT', 'secret')
PRISMA_API_URL = os.environ.get('PRISMA_API_URL') # e.g., 'https://api.prismacloud.io'

def lambda_handler(event, context):
    
    # --- 1. Log into Vault using IAM Role ---
    print("Authenticating to Vault using IAM role...")
    
    # Use boto3 to get credentials from the Lambda's execution environment
    session = boto3.Session()
    credentials = session.get_credentials()
    
    client = hvac.Client(url=VAULT_ADDR, namespace=VAULT_NAMESPACE)
    
    try:
        client.auth.aws.iam_login(
            access_key=credentials.access_key,
            secret_key=credentials.secret_key,
            session_token=credentials.token,
            role=VAULT_ROLE
        )
        
        if client.is_authenticated():
            print("Successfully authenticated to Vault.")
        else:
            raise Exception("Vault authentication failed.")
            
    except Exception as e:
        print(f"Error authenticating to Vault: {e}")
        return {"statusCode": 500, "body": "Vault auth failed"}

    # --- 2. List all secrets in the path ---
    print(f"Listing secrets at path: {VAULT_SECRETS_PATH}")
    try:
        list_response = client.secrets.kv.v2.list_secrets(
            path=VAULT_SECRETS_PATH,
            mount_point=VAULT_MOUNT_POINT
        )
        secret_names = list_response['data']['keys']
        print(f"Found {len(secret_names)} secrets to process.")
    except hvac.exceptions.InvalidPath:
        print(f"No secrets found at path: {VAULT_SECRETS_PATH}")
        return {"statusCode": 200, "body": "No secrets to process."}
    except Exception as e:
        print(f"Error listing secrets: {e}")
        return {"statusCode": 500, "body": "Failed to list secrets"}

    # --- 3, 4, & 5. Loop, Rotate, Update, and Deactivate ---
    for secret_name in secret_names:
        print(f"--- Processing secret: {secret_name} ---")
        try:
            # Read the current secret from Vault
            secret_path = f"{VAULT_SECRETS_PATH}/{secret_name}"
            secret_version = client.secrets.kv.v2.read_secret_version(
                path=secret_path,
                mount_point=VAULT_MOUNT_POINT
            )
            
            old_creds = secret_version['data']['data']
            old_access_key_id = old_creds.get('access_key_id')
            old_secret_key = old_creds.get('secret_key')

            if not old_access_key_id or not old_secret_key:
                print(f"Skipping {secret_name}: missing access_key_id or secret_key.")
                continue

            # --- 3a. Log into Prisma Cloud (to get a session token) ---
            # NOTE: This endpoint is an EXAMPLE. Check your Prisma Cloud API docs.
            print("Authenticating to Prisma Cloud...")
            auth_payload = {
                "accessKeyId": old_access_key_id,
                "secretKey": old_secret_key
            }
            auth_resp = requests.post(f"{PRISMA_API_URL}/login", json=auth_payload)
            auth_resp.raise_for_status() # Raise error on bad status
            
            prisma_token = auth_resp.json().get('token')
            if not prisma_token:
                raise Exception("Failed to get Prisma auth token.")
                
            api_headers = {'Authorization': f'Bearer {prisma_token}'}

            # --- 3b. List and delete inactive keys ---
            # NOTE: Endpoint is an EXAMPLE. Check your Prisma Cloud API docs.
            print("Listing and deleting inactive keys...")
            keys_resp = requests.get(f"{PRISMA_API_URL}/users/current/keys", headers=api_headers)
            keys_resp.raise_for_status()
            
            for key in keys_resp.json().get('keys', []):
                if key.get('status') == 'inactive' and key.get('id') != old_access_key_id:
                    print(f"Deleting inactive key: {key.get('id')}")
                    # NOTE: Endpoint is an EXAMPLE.
                    del_resp = requests.delete(f"{PRISMA_API_URL}/access_keys/{key.get('id')}", headers=api_headers)
                    if del_resp.status_code != 204:
                         print(f"Warning: Failed to delete inactive key {key.get('id')}")


            # --- 3c. Create a new access key ---
            # NOTE: Endpoint is an EXAMPLE. Check your Prisma Cloud API docs.
            print("Creating new access key...")
            create_payload = {"name": f"lambda-rotated-key-{context.aws_request_id}"}
            new_key_resp = requests.post(f"{PRISMA_API_URL}/users/current/keys", json=create_payload, headers=api_headers)
            new_key_resp.raise_for_status()
            
            new_key_data = new_key_resp.json()
            new_access_key_id = new_key_data['accessKeyId']
            new_secret_key = new_key_data['secretKey']
            print(f"Successfully created new key: {new_access_key_id}")

            # --- 4. Update the Vault secret with the new key ---
            print(f"Updating Vault secret: {secret_path}")
            new_secret_payload = {
                'access_key_id': new_access_key_id,
                'secret_key': new_secret_key
            }
            client.secrets.kv.v2.create_or_update_secret(
                path=secret_path,
                secret=new_secret_payload,
                mount_point=VAULT_MOUNT_POINT
            )
            print("Successfully updated Vault secret.")

            # --- 5. Set the old key to inactive ---
            # NOTE: Endpoint is an EXAMPLE. Check your Prisma Cloud API docs.
            print(f"Setting old key to inactive: {old_access_key_id}")
            disable_resp = requests.patch(
                f"{PRISMA_API_URL}/access_keys/{old_access_key_id}",
                json={"status": "inactive"},
                headers=api_headers
            )
            disable_resp.raise_for_status()
            print("Successfully set old key to inactive.")

        except Exception as e:
            # Log the error but continue to the next secret
            print(f"--- ERROR processing {secret_name}: {e} ---")

    print("--- Rotation process complete. ---")
    return {"statusCode": 200, "body": "Rotation process finished."}
