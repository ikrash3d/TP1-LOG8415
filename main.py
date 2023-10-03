import boto3
import os
from dotenv import load_dotenv

# from security_group import *


def create_security_group(group_name, description, client, vpc_id):
    response = client.create_security_group(
        GroupName=group_name, Description=description, VpcId=vpc_id
    )
    security_group_id = response["GroupId"]
    print(f"Security Group Created {security_group_id} in vpc")

    # Allow incoming traffic on port 80
    # security_group = client.SecurityGroup(security_group_id)
    # security_group.authorize_ingress(
    #     CidrIp="0.0.0.0/0", IpProtocol="tcp", FromPort=80, ToPort=80
    # )

    security_group_rules = [
        {
            "IpProtocol": "tcp",
            "FromPort": 80,
            "ToPort": 80,
            "IpRanges": [{"CidrIp": "0.0.0.0/0"}],
        },
        {
            "IpProtocol": "tcp",
            "FromPort": 22,
            "ToPort": 22,
            "IpRanges": [{"CidrIp": "0.0.0.0/0"}],
        },
    ]

    client.authorize_security_group_ingress(
        GroupId=security_group_id, IpPermissions=security_group_rules
    )

    return security_group_id


def create_ec2_instances(
    ami_id,
    instance_type,
    key_pair_name,
    resource,
    count=1,
    security_group_id=None,
):
    instances = resource.create_instances(
        ImageId=ami_id,
        InstanceType=instance_type,
        KeyName=key_pair_name["KeyName"],
        MinCount=count,
        MaxCount=count,
        SecurityGroupIds=[security_group_id] if security_group_id else [],
    )
    instance_ids = [instance.id for instance in instances]
    print("Instances", instance_ids, "have started.")
    return instance_ids


def create_load_balancer(security_group_id, client, subnets):
    response = client.create_load_balancer(
        Name="load-balancer-tp-1",
        Subnets=subnets,
        SecurityGroups=[security_group_id],
    )
    load_balancer_arn = response["LoadBalancers"][0]["LoadBalancerArn"]
    return load_balancer_arn


def create_target_group(client, vpc_id):
    response = client.create_target_group(
        Name="my-target-group", Protocol="HTTP", Port=80, VpcId=vpc_id
    )
    target_group_arn = response["TargetGroups"][0]["TargetGroupArn"]
    return target_group_arn


def register_targets(target_group_arn, instance_ids, client):
    targets = [{"Id": instance_id, "Port": 80} for instance_id in instance_ids]
    client.register_targets(TargetGroupArn=target_group_arn, Targets=targets)


def create_listener(load_balancer_arn, target_group_arn, client):
    client.create_listener(
        DefaultActions=[{"Type": "forward", "TargetGroupArn": target_group_arn}],
        LoadBalancerArn=load_balancer_arn,
        Port=80,
        Protocol="HTTP",
    )


def wait_for_instances_to_run(instance_ids, client, max_retries=10, delay=10):
    import time

    retries = 0
    while retries < max_retries:
        response = client.describe_instances(InstanceIds=instance_ids)
        all_running = all(
            [
                i["State"]["Name"] == "running"
                for r in response["Reservations"]
                for i in r["Instances"]
            ]
        )
        if all_running:
            return
        time.sleep(delay)
        retries += 1

    raise Exception("Instances did not transition to running state in time.")


if __name__ == "__main__":
    load_dotenv()
    aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    aws_region = os.getenv("AWS_REGION")
    aws_session_token = os.getenv("AWS_SESSION_TOKEN")
    aws_private_key = os.getenv("AWS_PRIVATE_KEY")

    ec2_resource = boto3.resource(
        "ec2",
        region_name=aws_region,
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        aws_session_token=aws_session_token,
    )

    ec2_client = boto3.client(
        "ec2",
        region_name=aws_region,
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        aws_session_token=aws_session_token,
    )

    elbv2_client = boto3.client(
        "elbv2",
        region_name=aws_region,
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        aws_session_token=aws_session_token,
    )

    ami_id = "ami-03a6eaae9938c858c"
    instance_type_t2_large = "t2.large"
    instance_type_m4_large = "m4.large"

    key_pair_name = ec2_client.create_key_pair(KeyName="my_key_pair")

    vpcs = ec2_client.describe_vpcs()
    vpc_id = vpcs.get("Vpcs", [{}])[0].get("VpcId", "")

    security_group_id = create_security_group(
        "security-group-lab-1", "the security lab 1 description", ec2_client, vpc_id
    )

    # instance_ids_m4_large = create_ec2_instances(
    #     ami_id,
    #     instance_type_m4_large,
    #     key_pair_name,
    #     count=5,
    #     security_group_id=security_group_id,
    # )

    instance_ids_t2_large = create_ec2_instances(
        ami_id,
        instance_type_t2_large,
        key_pair_name,
        ec2_resource,
        count=5,
        security_group_id=security_group_id,
    )

    sns = ec2_client.describe_subnets()
    subnets = []
    for sn in sns["Subnets"]:
        if (
            sn["AvailabilityZone"] == "us-east-1a"
            or sn["AvailabilityZone"] == "us-east-1b"
        ):
            subnets.append(sn["SubnetId"])

    load_balancer_arn = create_load_balancer(security_group_id, elbv2_client, subnets)
    target_group_arn = create_target_group(elbv2_client, vpc_id)

    # TDOD : Run the ec2instances before registering the targets\
    wait_for_instances_to_run(instance_ids_t2_large, ec2_client)

    register_targets(target_group_arn, instance_ids_t2_large, elbv2_client)
    create_listener(load_balancer_arn, target_group_arn, elbv2_client)
    print("Done")
