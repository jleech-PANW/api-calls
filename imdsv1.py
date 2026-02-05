#!/usr/bin/env python3
import boto3
from botocore.exceptions import ClientError
import argparse
import os

# This helper function is used to determine if a launch template is in use.
def is_launch_template_in_use(ec2_client, autoscaling_client, template_id, template_name):
    """
    Checks if a launch template is in use by an ASG or running EC2 instance.
    Returns a simple string summary.
    """
    # 1. Check Auto Scaling Groups
    try:
        paginator = autoscaling_client.get_paginator('describe_auto_scaling_groups')
        for page in paginator.paginate():
            for asg in page['AutoScalingGroups']:
                lt_spec = asg.get('LaunchTemplate') or \
                          asg.get('MixedInstancesPolicy', {}).get('LaunchTemplate', {}).get('LaunchTemplateSpecification')
                if lt_spec and (lt_spec.get('LaunchTemplateId') == template_id or lt_spec.get('LaunchTemplateName') == template_name):
                    return f"Yes (ASG: {asg['AutoScalingGroupName']})"
    except ClientError as e:
        if e.response['Error']['Code'] == 'AccessDenied':
            return "Unknown (ASG check failed)"
        print(f"Warning: Could not check ASGs for {template_name}: {e}")

    # === FIX STARTS HERE ===
    # 2. Check running EC2 instances using a client-side filter for maximum compatibility.
    try:
        paginator = ec2_client.get_paginator('describe_instances')
        pages = paginator.paginate(
            Filters=[{'Name': 'instance-state-name', 'Values': ['pending', 'running']}]
        )
        for page in pages:
            for reservation in page['Reservations']:
                for instance in reservation['Instances']:
                    instance_lt = instance.get('LaunchTemplate')
                    if instance_lt and instance_lt.get('LaunchTemplateId') == template_id:
                        return f"Yes (Instance: {instance['InstanceId']})"
    except ClientError as e:
        if e.response['Error']['Code'] == 'AccessDenied':
            return "Unknown (EC2 check failed)"
        # The original error occurred here. We are now handling it differently.
        print(f"Warning: Could not check EC2 Instances for {template_name}: {e}")
    # === FIX ENDS HERE ===

    return "No"

def find_imds_v1_launch_templates(region):
    """
    Finds all launch templates in a region that have IMDSv1 enabled on their
    default version and checks if they are in use.
    """
    print(f"[*] Searching for launch templates with IMDSv1 enabled in region: {region}\n")
    ec2_client = boto3.client('ec2', region_name=region)
    autoscaling_client = boto3.client('autoscaling', region_name=region)
    
    vulnerable_templates = []
    
    try:
        paginator = ec2_client.get_paginator('describe_launch_templates')
        for page in paginator.paginate():
            for lt in page['LaunchTemplates']:
                lt_name = lt['LaunchTemplateName']
                lt_id = lt['LaunchTemplateId']
                default_version_num = lt['DefaultVersionNumber']

                versions_response = ec2_client.describe_launch_template_versions(
                    LaunchTemplateId=lt_id,
                    Versions=[str(default_version_num)]
                )
                
                if not versions_response['LaunchTemplateVersions']:
                    continue

                metadata_options = versions_response['LaunchTemplateVersions'][0]['LaunchTemplateData'].get('MetadataOptions', {})
                http_tokens = metadata_options.get('HttpTokens', 'optional')

                if http_tokens == 'optional':
                    in_use_status = is_launch_template_in_use(ec2_client, autoscaling_client, lt_id, lt_name)
                    vulnerable_templates.append({
                        "Name": lt_name,
                        "ID": lt_id,
                        "DefaultVersion": default_version_num,
                        "HttpTokens": http_tokens,
                        "InUse": in_use_status
                    })
    
    except ClientError as e:
        print(f"An error occurred: {e}")
        return

    if not vulnerable_templates:
        print("[-] No launch templates found with IMDSv1 enabled. Well done!")
        return

    # --- Print a formatted table ---
    headers = ["Launch Template Name", "ID", "Default Version", "In Use?"]
    name_w = max([len(h["Name"]) for h in vulnerable_templates] + [len(headers[0])])
    id_w = max([len(h["ID"]) for h in vulnerable_templates] + [len(headers[1])])
    ver_w = len(headers[2])
    use_w = max([len(h["InUse"]) for h in vulnerable_templates] + [len(headers[3])])

    print(f"{headers[0]:<{name_w}} | {headers[1]:<{id_w}} | {headers[2]:<{ver_w}} | {headers[3]:<{use_w}}")
    print(f"{'-'*name_w}-+-{'-'*id_w}-+-{'-'*ver_w}-+-{'-'*use_w}")

    for lt in vulnerable_templates:
        print(f"{lt['Name']:<{name_w}} | {lt['ID']:<{id_w}} | {str(lt['DefaultVersion']):<{ver_w}} | {lt['InUse']:<{use_w}}")


if __name__ == "__main__":
    default_region = os.environ.get('AWS_REGION', 'us-east-1')
    
    parser = argparse.ArgumentParser(description="Find AWS Launch Templates with IMDSv1 enabled.")
    parser.add_argument(
        '--region',
        type=str,
        default=default_region,
        help=f"The AWS region to scan. Defaults to your CloudShell region ({default_region})."
    )
    args = parser.parse_args()
    
    find_imds_v1_launch_templates(args.region)
