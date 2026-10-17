import json

import boto3

REGION = "us-east-2"

ec2 = boto3.client("ec2", region_name=REGION)
s3 = boto3.client("s3", region_name=REGION)
rds = boto3.client("rds", region_name=REGION)
sts = boto3.client("sts", region_name=REGION)

ids = {}


def save():
    with open("ids.json", "w") as f:
        json.dump(ids, f, indent=2)


account_id = sts.get_caller_identity()["Account"]
print("Running as:", sts.get_caller_identity()["Arn"])

vpc_id = ec2.describe_vpcs(Filters=[{"Name": "isDefault", "Values": ["true"]}])["Vpcs"][0]["VpcId"]

ec2_sg = ec2.create_security_group(
    GroupName="lab-ec2-sg", Description="Grupo de seguridad para la instancia de EC2 de la actividad", VpcId=vpc_id
)["GroupId"]
ids["ec2_sg"] = ec2_sg
save()

rds_sg = ec2.create_security_group(
    GroupName="lab-rds-sg", Description="Permite PostgreSQL solamente desde la instancia de EC2 de la actividad", VpcId=vpc_id
)["GroupId"]
ids["rds_sg"] = rds_sg
save()

ec2.authorize_security_group_ingress(
    GroupId=rds_sg,
    IpPermissions=[
        {
            "IpProtocol": "tcp",
            "FromPort": 5432,
            "ToPort": 5432,
            "UserIdGroupPairs": [{"GroupId": ec2_sg}],
        }
    ],
)
print("Security groups created")

bucket = f"lab-bucket-{account_id}"
s3.create_bucket(Bucket=bucket, CreateBucketConfiguration={"LocationConstraint": REGION})
ids["bucket"] = bucket
save()
print("Bucket created:", bucket)

images = ec2.describe_images(
    Owners=["amazon"],
    Filters=[
        {"Name": "name", "Values": ["al2023-ami-2023*-x86_64"]},
        {"Name": "state", "Values": ["available"]},
    ],
)["Images"]
ami = sorted(images, key=lambda i: i["CreationDate"])[-1]["ImageId"]

instance_id = ec2.run_instances(
    ImageId=ami,
    InstanceType="t3.micro",
    MinCount=1,
    MaxCount=1,
    SecurityGroupIds=[ec2_sg],
    TagSpecifications=[
        {"ResourceType": "instance", "Tags": [{"Key": "Name", "Value": "lab-ec2"}]}
    ],
)["Instances"][0]["InstanceId"]
ids["instance"] = instance_id
save()
print("EC2 instance created:", instance_id)

rds.create_db_instance(
    DBInstanceIdentifier="lab-db",
    Engine="postgres",
    DBInstanceClass="db.t3.micro",
    AllocatedStorage=20,
    MasterUsername="dbadmin",
    ManageMasterUserPassword=True,
    VpcSecurityGroupIds=[rds_sg],
    PubliclyAccessible=False,
    BackupRetentionPeriod=0,
)
ids["db"] = "lab-db"
save()
print("RDS creation started. Waiting (5-10 minutes)...")

ec2.get_waiter("instance_running").wait(InstanceIds=[instance_id])
rds.get_waiter("db_instance_available").wait(DBInstanceIdentifier="lab-db")

db = rds.describe_db_instances(DBInstanceIdentifier="lab-db")["DBInstances"][0]
print("RDS endpoint:", db["Endpoint"]["Address"])
print("Password secret:", db["MasterUserSecret"]["SecretArn"])
print("Done. Everything is running.")
