import io
import time
import uuid

import boto3
import botocore
from click import echo, secho
import paramiko

from . import userdata

# Ubuntu 16.04 hvm ebs ssd
IMAGES = {
    'us-east-1':        'ami-2ef48339',  # nvirg
    'us-west-1':        'ami-a9a8e4c9',  # calif
    'us-west-2':        'ami-746aba14',  # oregon
    'eu-west-1':        'ami-0ae77879',  # ireland ubuntu/images/hvm-ssd/ubuntu-xenial-16.04-amd64-server-20160610
    'eu-central-1':     'ami-a9a557c6',  # frankfurt
    'ap-northeast-1':   'ami-0919cd68',  # tokyo
    'ap-northeast-2':   'ami-4124f12f',  # seoul ubuntu/images/hvm-ssd/ubuntu-xenial-16.04-amd64-server-20160721
    'ap-southeast-1':   'ami-42934921',  # singapore
    'ap-southeast-2':   'ami-623c0d01',  # sydney
    'ap-south-1':       'ami-7e94fe11',  # mumbai
    'sa-east-1':        'ami-60bd2d0c',  # sao paulo
}

supported_regions = ['us-east-1', 'us-west-1', 'us-west-2', 'eu-west-1', 'eu-central-1',
    'ap-northeast-1', 'ap-northeast-2', 'ap-southeast-1', 'ap-southeast-2', 'ap-south-1',
    'sa-east-1']

def aws_create_cassandra(nodes=1, region=None, storage_gbs=8, flavor='t2.micro'):
    """Create Cassandra cluster in AWS."""
    cluster_uuid = uuid.uuid4().hex
    secho('Cluster UUID is ' + cluster_uuid, fg='green', blink=True)

    if region:
        if region not in IMAGES.keys():
            secho('Invalid region: ' + region, err=True, fg='red')
        ec2 = boto3.resource('ec2', region_name=region)
    else:
        ec2 = boto3.resource('ec2')

    key_name = 'cassandra_keypair_' + cluster_uuid
    secho('Creating keypair ' + key_name + ' ...')
    # On the first actual connection to AWS, we can check if our credentials
    # are invalid. No need to check afterwards.
    try:
        keypair = ec2.create_key_pair(KeyName=key_name)
    except botocore.exceptions.ClientError:
        secho('Invalid credentials', err=True, fg='red')
        return
    secho('Keypair ' + key_name + ' created.', fg='green')
    secho('Private key:')
    secho(keypair.key_material)

    secgroup_name = 'cassandra_sg_' + cluster_uuid
    secho('Creating security group ' + secgroup_name + \
            ' With open ports 80,22,443,6666-9999 open ...')
    description = 'Security group for Cassandra cluster'
    ip_portrange_tuples = [
        ('0.0.0.0/0', 80, 80),
        ('0.0.0.0/0', 22, 22),
        ('0.0.0.0/0', 443, 443),
        ('0.0.0.0/0', 6666, 9999),
    ]
    mysg = ec2.create_security_group(GroupName=secgroup_name,
            Description=description)
    for ip, start_port, end_port in ip_portrange_tuples:
        mysg.authorize_ingress(IpProtocol="tcp", CidrIp=ip,
                FromPort=start_port, ToPort=end_port)
    secho('Security group ' + secgroup_name + ' created.', fg='green')

    # Spawn VMs in AWS, and wait till all of them are running, and then return.

    # First create seed node, wait for it to be in 'running' state, then create
    # non seed nodes, then wait for all of them to be in running, and then
    # return all node's public IP addresses.

    count = nodes
    all_instance_ids = []

    secho('Creating ' + str(nodes) + ' instance(s) ...')

    # TODO(rushiagr): retry 5 times when an exception occurs which we know we
    # can retry 'e.g. connection timeout. Also identify if the credentials are
    # wrong, in that case don't retry and return error to user.
    try:
        # Will default to 8 gb root volume
        instances = ec2.create_instances(#DryRun=True,
                ImageId=IMAGES[region], UserData=userdata.seed_userdata,
                MinCount=1, MaxCount=1, InstanceType=flavor,
                KeyName=key_name, SecurityGroupIds=[mysg.id])
    except Exception as e:
        secho('exception thrown: ' + str(e), err=True, fg='red')
        return

    instances = list(instances)
    ids = [i.id for i in instances]
    all_instance_ids.append(ids[0])

    seed_private_ip_address = None

    while True:
        instances = ec2.instances.filter(InstanceIds=ids)
        instances = [i for i in instances]
        seed_private_ip_address = instances[0].private_ip_address
        if seed_private_ip_address is not None:
            break
        time.sleep(5)


    non_seed_userdata = userdata.non_seed_userdata.replace(
            '__SEEDS__', seed_private_ip_address)

    count -= 1

    if count != 0:
        # TODO(rushiagr): retry 5 times when an exception occurs which we know
        # we can retry 'e.g. connection timeout. Also identify if the
        # credentials are wrong, in that case don't retry and return error to
        # user.
        try:
            # Will default to 8 gb root volume
            instances = ec2.create_instances(#DryRun=True,
                    ImageId=IMAGES[region], UserData=non_seed_userdata,
                    MinCount=count, MaxCount=count,
                    InstanceType=flavor, KeyName=key_name,
                    SecurityGroupIds=[mysg.id])
        except Exception as e:
            secho('exception thrown: ' + e, err=True, fg='red')
            return

        instances = list(instances)
        ids = [i.id for i in instances]
        all_instance_ids.extend(ids)

    # Waiting for instances to all have state = 'running'
    # TODO(rushiagr): retry if instances go in error state. Even better - use
    # autoscaling group
    while True:
        instances = ec2.instances.filter(InstanceIds=all_instance_ids)
        states = [i.state['Name'] for i in instances]
        non_running_states = [state for state in states if state != 'running']
        if len(non_running_states) == 0:
            break
        time.sleep(5)

    secho('All instances now in running state.', fg='green')
    secho('Waiting for all instances to join the cassandra cluster. '
            'This might take a while.')

    ips = [i.public_ip_address for i in instances]

    # Ensure cassandra cluster is created by checking 'nodetool status' on each
    # server.  Wait till all nodes' 'nodetool status' shows that all nodes have
    # joined the cluster.

    pvt_key = paramiko.RSAKey.from_private_key(
                    io.StringIO(keypair.key_material))

    connections = {}
    successful_creations = True
    while True:
        for ip in ips:
            try:
                ssh = paramiko.SSHClient()
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                ssh.connect(ip, username='ubuntu', pkey=pvt_key)
                connections[ip] = ssh
            except paramiko.ssh_exception.NoValidConnectionsError as e:

                # TODO(rushiagr): handle
                # paramiko.ssh_exception.AuthenticationException when
                # authentication exception occurs

                # print('exception thrown, retrying')
                # print(e)
                successful_creations = False
                time.sleep(5)
                break

        if successful_creations:
            break
        successful_creations = True
        time.sleep(5)

    while True:
        all_fine = True
        for ip, conn in connections.items():
            stdin, stdout, err = ssh.exec_command("nodetool status")
            stdin.close()
            stdout = stdout.read()
            err = err.read()
            # print('stdout is')
            # print(stdout)
            # print('err is', err)
            # print('nodetool status output for', ip, 'is:\n', stdout)

            stdin, stdout, err = ssh.exec_command(
                "nodetool status | grep ^UN | grep -v '127.0.0.1' | wc | awk '{print $1}' ")
            stdin.close()
            stdout = stdout.read()
            err = err.read()
            # print('stdout is')
            # print(stdout)
            # print('err is', err)
            # print('nodetool num of nodes output for', ip, 'is:\n', stdout)

            if not int(stdout.strip()) == len(ips):
                all_fine = False

        if all_fine:
            [ssh.close() for ssh in connections.values()]
            secho('Cluster creation complete!', fg='green', blink=True)
            return

        time.sleep(5)
