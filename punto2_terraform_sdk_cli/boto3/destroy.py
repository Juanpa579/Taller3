import json

import boto3
from botocore.exceptions import ClientError

REGION = "us-east-2"

ec2 = boto3.client("ec2", region_name=REGION)
s3 = boto3.resource("s3", region_name=REGION)
rds = boto3.client("rds", region_name=REGION)

with open("ids.json") as f:
    ids = json.load(f)

if "instance" in ids:
    ec2.terminate_instances(InstanceIds=[ids["instance"]])
    print("Terminating EC2...")

if "db" in ids:
    try:
        rds.delete_db_instance(
            DBInstanceIdentifier=ids["db"],
            SkipFinalSnapshot=True,
            DeleteAutomatedBackups=True,
        )
        print("Deleting RDS (5-10 minutes)...")
        rds.get_waiter("db_instance_deleted").wait(DBInstanceIdentifier=ids["db"])
    except ClientError as e:
        print("RDS:", e.response["Error"]["Message"])

if "instance" in ids:
    ec2.get_waiter("instance_terminated").wait(InstanceIds=[ids["instance"]])

for key in ("rds_sg", "ec2_sg"):
    if key in ids:
        try:
            ec2.delete_security_group(GroupId=ids[key])
            print("Deleted", key)
        except ClientError as e:
            print(key, e.response["Error"]["Message"])

if "bucket" in ids:
    bucket = s3.Bucket(ids["bucket"])
    bucket.objects.all().delete()
    bucket.delete()
    print("Deleted bucket", ids["bucket"])

print("Done.")
