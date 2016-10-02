import click
from click import echo, secho

from . import server

@click.command()
@click.option('--region', '-n', help='AWS region. Defaults to us-east-1.')
@click.option('--nodes', '-n', default=1,
        help='Number of nodes in cluster. Defaults to 1')
@click.option('--storage-gbs', '-s', default=8,
        help='Root disk size in GBs. Defaults to 8.')
@click.option('--instance-type', '-i', default='t2.micro',
        help='AWS instance type. Defaults to t2.micro.')
@click.argument('cluster', default='cassandra', required=True)
def main(cluster, instance_type, storage_gbs, nodes, region):
    if cluster != 'cassandra':
        secho('Cluster "%s" not supported' % cluster, err=True, fg='red')
        return
    server.aws_create_cassandra(nodes=nodes, region=region,
            storage_gbs=storage_gbs, flavor=instance_type)


# TODO(rushiagr): don't use mysg but a better var name

# TODO(rushiagr): wait till completion in boto3, and don't write 'while' loop
# in code

# TODO(rushiagr): add cluster_uuid as tags to all resources, so they can be
# deleted easily

# TODO(rushiagr): support for ec2 profiles.

# TODO(rushiagr): add test: if no .aws/credentials file is present, raise error
# saying 'please `aws configure`'

# TODO(rushiagr): specify an existing keypair and security group with --keypair
# and --security-group command line options

# TODO(rushiagr): Say 'script completed in 1234 seconds' at end

# TODO(rushiagr): Display public IPs of nodes in cluster, for easy viewing
