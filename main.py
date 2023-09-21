import boto3
from security_group import *


def create_security_group(group_name, description):
    response = ec2.create_security_group(GroupName=group_name, Description=description)
    security_group_id = response["GroupId"]
    print(f"Security Group Created {security_group_id} in vpc")

    # Allow incoming traffic on port 80
    security_group = ec2.SecurityGroup(security_group_id)
    security_group.authorize_ingress(
        CidrIp="0.0.0.0/0", IpProtocol="tcp", FromPort=80, ToPort=80
    )

    return security_group_id


def create_ec2_instances(
    ami_id, instance_type, key_pair_name, count=1, security_group_id=None
):
    instances = ec2.create_instances(
        ImageId=ami_id,
        InstanceType=instance_type,
        KeyName=key_pair_name,
        MinCount=5,
        MaxCount=count,
        SecurityGroupIds=[security_group_id] if security_group_id else [],
    )
    instance_ids = [instance.id for instance in instances]
    print("Instances", instance_ids, "have started.")
    return instance_ids


def create_load_balancer(security_group_id):
    response = client.create_load_balancer(
        Name="my-load-balancer",
        Subnets=["subnet-id1", "subnet-id2"],  # Replace with your subnet IDs
        SecurityGroups=[security_group_id],
    )
    load_balancer_arn = response["LoadBalancers"][0]["LoadBalancerArn"]
    return load_balancer_arn


def create_target_group():
    response = client.create_target_group(
        Name="my-target-group",
        Protocol="HTTP",
        Port=80,
        VpcId="your-vpc-id",  # Replace with your VPC ID
    )
    target_group_arn = response["TargetGroups"][0]["TargetGroupArn"]
    return target_group_arn


def register_targets(target_group_arn, instance_ids):
    targets = [{"Id": instance_id, "Port": 80} for instance_id in instance_ids]
    client.register_targets(TargetGroupArn=target_group_arn, Targets=targets)


def create_listener(load_balancer_arn, target_group_arn):
    client.create_listener(
        DefaultActions=[{"Type": "forward", "TargetGroupArn": target_group_arn}],
        LoadBalancerArn=load_balancer_arn,
        Port=80,
        Protocol="HTTP",
    )


if __name__ == "__main__":
    ec2 = boto3.resource("ec2")
    client = boto3.client("elbv2")

    ami_id = "ami-xxxxxxxxxxxxxxxxx"  # Replace with your AMI ID
    instance_type_t2_large = "t2.large"
    instance_type_m4_large = "m4.large"

    key_pair_name = "your_key_pair_name"

    security_group_id = create_security_group(
        "my-security-group", "My security group description"
    )
    instance_ids_m4_large = create_ec2_instances(
        ami_id,
        instance_type_m4_large,
        key_pair_name,
        count=5,
        security_group_id=security_group_id,
    )
    instance_ids_t2_large = create_ec2_instances(
        ami_id,
        instance_type_t2_large,
        key_pair_name,
        count=5,
        security_group_id=security_group_id,
    )
    load_balancer_arn = create_load_balancer(security_group_id)
    target_group_arn = create_target_group()
    register_targets(target_group_arn, instance_ids)
    create_listener(load_balancer_arn, target_group_arn)

    # Creating session
    # session = boto3.session(profile_name="default")

    # ec2_ressource = session.resource("ec2")
    # elb_client = session.client("elbv2")
    # ec2_client = session.client("ec2")

    # # create security group
    # vpcs = ec2_client.describe_vpcs()
    # vpc_id = vpcs.get("Vpcs", [{}])[0].get("VpcId", "")

    # security_group = create_security_group(ec2_client, vpc_id)

    # create target group
    # cluster1 = create_target_groups(elb_client, "cluster1", vpc_id)["TargetGroups"][0]
    # cluster2 = create_target_groups(elb_client, "cluster2", vpc_id)["TargetGroups"][0]

    # target_groups = [cluster1["TargetGroupArn"], cluster2["TargetGroupArn"]]

    # security_groups = [sg["GroupId"]]

    # sn_all = ec2_client.describe_subnets()
    # subnets = []
    # for sn in sn_all["Subnets"]:
    #     if (
    #         sn["AvailabilityZone"] == "us-east-1a"
    #         or sn["AvailabilityZone"] == "us-east-1b"
    #     ):
    #         subnets.append(sn["SubnetId"])

    # load_balancer = create_load_balancer(
    #     elb_client, subnets, security_groups, target_groups
    # )

    # write_file_content(load_balancer["LoadBalancerDNS"])

    # key_pair = create_key_pair(ec2_client, "key_pair")
    # try:
    #     # cluster 1 instances
    #     create_instances(
    #         ec2_resource,
    #         instances_ami,
    #         "t2.large",
    #         "key_pair",
    #         "cluster1",
    #         subnets[0],
    #         3,
    #         sg["GroupId"],
    #     )
    #     create_instances(
    #         ec2_resource,
    #         instances_ami,
    #         "t2.large",
    #         "key_pair",
    #         "cluster1",
    #         subnets[1],
    #         2,
    #         sg["GroupId"],
    #     )

    #     # cluster 2 instances
    #     create_instances(
    #         ec2_resource,
    #         instances_ami,
    #         "m4.large",
    #         "key_pair",
    #         "cluster2",
    #         subnets[1],
    #         2,
    #         sg["GroupId"],
    #     )
    #     create_instances(
    #         ec2_resource,
    #         instances_ami,
    #         "m4.large",
    #         "key_pair",
    #         "cluster2",
    #         subnets[0],
    #         2,
    #         sg["GroupId"],
    #     )

    #     print("Instances created")
    # except Exception as e:
    #     print(e)
