#!/usr/bin/env bash
set -uo pipefail
export AWS_PAGER=""
REGION="us-east-2"
 
source ./ids.env
 
if [ -n "${INSTANCE_ID:-}" ]; then
    aws ec2 terminate-instances --region "$REGION" --instance-ids "$INSTANCE_ID" > /dev/null
    echo "Terminating EC2..."
fi
 
if aws rds describe-db-instances --region "$REGION" --db-instance-identifier lab-db > /dev/null 2>&1; then
    aws rds delete-db-instance --region "$REGION" --db-instance-identifier lab-db \
        --skip-final-snapshot --delete-automated-backups > /dev/null
    echo "Deleting RDS (5-10 minutes)..."
    aws rds wait db-instance-deleted --region "$REGION" --db-instance-identifier lab-db
fi
 
if [ -n "${INSTANCE_ID:-}" ]; then
    aws ec2 wait instance-terminated --region "$REGION" --instance-ids "$INSTANCE_ID"
fi
 
aws ec2 delete-security-group --region "$REGION" --group-id "$RDS_SG" && echo "Deleted $RDS_SG"
aws ec2 delete-security-group --region "$REGION" --group-id "$EC2_SG" && echo "Deleted $EC2_SG"
 
aws s3 rb "s3://$BUCKET" --force
 
echo "Done."