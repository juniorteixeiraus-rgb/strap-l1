#!/usr/bin/env python3
"""
STRAP 722 — Complete Network Deployment Script
=================================================
Deploys the full 722 blockchain network on AWS:
- CloudFormation stack (VPC, subnets, security group, IAM, S3, EC2)
- EC2 instance with 722 node software
- S3 bucket for state storage
- CloudWatch alarms
"""

import json
import os
import subprocess
import sys
import time
import boto3
from botocore.exceptions import ClientError

AWS_REGION = "us-east-1"
PROFILE = "722strap"
CF_STACK_NAME = "strap722-network"
CF_TEMPLATE = "/tmp/strap722-cf.json"

class Bcolors:
    OK = "\033[92m"
    ERROR = "\033[91m"
    WARN = "\033[93m"
    ACTION = "\033[96m"
    RESET = "\033[0m"

def log(msg, color=Bcolors.OK):
    print(f"{color}{msg}{Bcolors.RESET}")

def run(cmd, timeout=120):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.stdout + r.stderr, r.returncode
    except subprocess.TimeoutExpired:
        return "TIMEOUT", 1
    except Exception as e:
        return f"ERROR: {e}", 1

def main():
    print("=" * 60)
    print("STRAP 722 — AWS Network Deployment")
    print("=" * 60)

    # Check if AWS credentials are available
    print("\n[1] Checking AWS credentials...")
    out, code = run(["/tmp/awscli/aws/dist/aws", "sts", "get-caller-identity", "--profile", PROFILE], timeout=30)
    if code != 0 or "Account" not in out:
        print(f"{Bcolors.WARN}[!] AWS credentials not available")
        print(f"   Run: /tmp/awscli/aws/dist/aws sso login --profile {PROFILE}")
        print(f"   Then complete browser login, then re-run this script")
        print()
        print("Alternative: Deploy CloudFormation manually with AWS console")
        print(f"  aws cloudformation create-stack \\")
        print(f"    --stack-name {CF_STACK_NAME} \\")
        print(f"    --template-body file://{CF_TEMPLATE} \\")
        print(f"    --capabilities CAPABILITY_IAM \\")
        print(f"    --profile {PROFILE}")
        return False

    identity = json.loads(out)
    print(f"   Account: {identity.get('Account')}")
    print(f"   ARN: {identity.get('Arn')}")
    print(f"{Bcolors.OK}[OK] AWS credentials working{Bcolors.RESET}")

    # Check if CloudFormation stack already exists
    print(f"\n[2] Checking for existing stack '{CF_STACK_NAME}'...")
    try:
        cf = boto3.client("cloudformation", region_name=AWS_REGION,
                            aws_access_key_id="",
                            aws_secret_access_key="",
                            aws_session_token="")
        # Try with default credentials
        cf = boto3.client("cloudformation", region_name=AWS_REGION)
        stacks = cf.list_stacks(
            StackStatusFilter=["CREATE_IN_PROGRESS", "CREATE_COMPLETE", "UPDATE_IN_PROGRESS"]
        )
        for s in stacks.get("StackSummaries", []):
            if s["StackName"] == CF_STACK_NAME:
                print(f"{Bcolors.WARN}[!] Stack already exists: {s['StackId']}")
                print("   Update with: aws cloudformation update-stack ...")
                print("   Or delete and recreate: aws cloudformation delete-stack --stack-name " + CF_STACK_NAME)
                return True  # Stack exists, deployment can be done manually
    except Exception as e:
        print(f"   Could not check stacks: {e}")

    # Deploy CloudFormation stack
    print(f"\n[3] Deploying CloudFormation stack '{CF_STACK_NAME}'...")
    print(f"   Template: {CF_TEMPLATE}")
    print(f"   Region: {AWS_REGION}")

    if not os.path.exists(CF_TEMPLATE):
        print(f"{Bcolors.ERROR}[!] Template not found: {CF_TEMPLATE}")
        return False

    try:
        with open(CF_TEMPLATE) as f:
            template_body = f.read()

        cf = boto3.client("cloudformation", region_name=AWS_REGION)

        response = cf.create_stack(
            StackName=CF_STACK_NAME,
            TemplateBody=template_body,
            Capabilities=["CAPABILITY_IAM"],
            Tags=[
                {"Key": "Project", "Value": "Strap722"},
                {"Key": "Environment", "Value": "production"},
            ]
        )

        stack_id = response.get("StackId", "")
        print(f"   Stack ID: {stack_id}")
        print(f"{Bcolors.OK}[OK] Stack creation initiated{Bcolors.RESET}")

        # Wait for stack to complete
        print("\n[4] Waiting for stack to complete...")
        waiter = cf.get_waiter("stack_create_complete")
        try:
            waiter.wait(
                StackName=CF_STACK_NAME,
                WaiterConfig={
                    "Delay": 30,
                    "MaxAttempts": 60,
                }
            )
            print(f"{Bcolors.OK}[OK] Stack creation complete{Bcolors.RESET}")
        except Exception as e:
            print(f"{Bcolors.WARN}[!] Stack creation may still be in progress: {e}")

        # Get stack outputs
        print("\n[5] Getting stack outputs...")
        try:
            response = cf.describe_stacks(StackName=CF_STACK_NAME)
            stack = response.get("Stacks", [{}])[0]
            outputs = stack.get("Outputs", [])

            print("\n  --- Stack Outputs ---")
            for out in outputs:
                key = out.get("OutputKey", "")
                value = out.get("OutputValue", "")
                print(f"  {key}: {value}")

            # Extract key outputs
            vpc_id = None
            subnet_id = None
            sg_id = None
            s3_bucket = None
            instance_id = None

            for out in outputs:
                key = out.get("OutputKey", "")
                value = out.get("OutputValue", "")
                if key == "VPCId":
                    vpc_id = value
                elif key == "Subnet1Id":
                    subnet_id = value
                elif key == "SecurityGroupId":
                    sg_id = value
                elif key == "S3BucketName":
                    s3_bucket = value
                elif key == "Node1InstanceId":
                    instance_id = value

            print(f"\n{Bcolors.OK}[OK] Deployment complete{Bcolors.RESET}")
            print(f"\n  --- Network Summary ---")
            print(f"  VPC: {vpc_id}")
            print(f"  Subnet: {subnet_id}")
            print(f"  Security Group: {sg_id}")
            print(f"  S3 Bucket: {s3_bucket}")
            print(f"  EC2 Instance: {instance_id}")
            print(f"\n  Next steps:")
            print(f"  1. SSH to instance: ssh -i ~/.ssh/strap722-key.pem ec2-user@<public-ip>")
            print(f"  2. Deploy 722 node software to EC2")
            print(f"  3. Start LHS network node")
            print(f"  4. Configure cross-chain anchors (Base + Solana)")

            return True

        except Exception as e:
            print(f"{Bcolors.WARN}[!] Could not get outputs: {e}")
            return True  # Stack may still be creating

    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "")
        if error_code == "AlreadyExistsException":
            print(f"{Bcolors.WARN}[!] Stack already exists")
            return True
        elif error_code == "AccessDenied":
            print(f"{Bcolors.ERROR}[!] Access denied - check IAM permissions")
            return False
        else:
            print(f"{Bcolors.ERROR}[!] CloudFormation error: {e}")
            return False
    except Exception as e:
        print(f"{Bcolors.ERROR}[!] Deployment error: {e}")
        return False

if __name__ == "__main__":
    try:
        success = main()
    except KeyboardInterrupt:
        print("\nInterrupted.")
        success = False
    except Exception as e:
        print(f"\nFatal: {e}")
        import traceback
        traceback.print_exc()
        success = False
    sys.exit(0 if success else 1)
