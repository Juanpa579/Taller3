#!/usr/bin/env bash
set -euo pipefail
export AWS_PAGER=""
REGION="us-east-2"
 
ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
echo "Account: $ACCOUNT"
 
VPC_ID=$(aws ec2 describe-vpcs --region "$REGION" --filters Name=isDefault,Values=true \
    --query "Vpcs[0].VpcId" --output text)
 
EC2_SG=$(aws ec2 create-security-group --region "$REGION" --group-name lab-ec2-sg \
    --description "Grupo de seguridad para la instancia de EC2 de la actividad" --vpc-id "$VPC_ID" \
    --query GroupId --output text)
 
RDS_SG=$(aws ec2 create-security-group --region "$REGION" --group-name lab-rds-sg \
    --description "Permite PostgreSQL solamente desde la instancia de EC2 de la actividad" --vpc-id "$VPC_ID" \
    --query GroupId --output text)
 
BUCKET="lab-bucket-$ACCOUNT"
cat > ids.env <<EOF
EC2_SG=$EC2_SG
RDS_SG=$RDS_SG
BUCKET=$BUCKET
EOF
 
aws ec2 authorize-security-group-ingress --region "$REGION" --group-id "$RDS_SG" \
    --protocol tcp --port 5432 --source-group "$EC2_SG" > /dev/null
echo "Security groups created: $EC2_SG, $RDS_SG"
 
aws s3api create-bucket --region "$REGION" --bucket "$BUCKET" \
    --create-bucket-configuration LocationConstraint="$REGION" > /dev/null
echo "Bucket created: $BUCKET"
 
AMI=$(aws ec2 describe-images --region "$REGION" --owners amazon \
    --filters "Name=name,Values=al2023-ami-2023*-x86_64" "Name=state,Values=available" \
    --query "sort_by(Images,&CreationDate)[-1].ImageId" --output text)
 
INSTANCE_ID=$(aws ec2 run-instances --region "$REGION" --image-id "$AMI" --instance-type t3.micro \
    --security-group-ids "$EC2_SG" --count 1 \
    --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=lab-ec2}]" \
    --query "Instances[0].InstanceId" --output text)
echo "INSTANCE_ID=$INSTANCE_ID" >> ids.env
echo "EC2 instance created: $INSTANCE_ID"
 
aws rds create-db-instance --region "$REGION" --db-instance-identifier lab-db \
    --engine postgres --db-instance-class db.t3.micro --allocated-storage 20 \
    --master-username dbadmin --manage-master-user-password \
    --vpc-security-group-ids "$RDS_SG" --no-publicly-accessible \
    --backup-retention-period 0 > /dev/null
echo "RDS creation started. Waiting (5-10 minutes)..."
 
aws ec2 wait instance-running --region "$REGION" --instance-ids "$INSTANCE_ID"
aws rds wait db-instance-available --region "$REGION" --db-instance-identifier lab-db
 
aws rds describe-db-instances --region "$REGION" --db-instance-identifier lab-db \
    --query "DBInstances[0].[Endpoint.Address,MasterUserSecret.SecretArn]" --output text
echo "Done. Everything is running."