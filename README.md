# <a href="quick-cluster.github.com">Quick Cluster</a>

Quickly and easily create a Cassandra cluster on EC2 cloud.


# Installation

Clone this repository, and run `python setup.py develop`

# Usage

Example:

    $ qc --nodes 5 --storage-gbs 100 --instance-type m4.large --region us-west-1

View all options:

    $ qc --help
    Usage: qc [OPTIONS] CLUSTER
    .
    Options:
      -n, --region TEXT          AWS region. Defaults to us-east-1.
      -n, --nodes INTEGER        Number of nodes in cluster. Defaults to 1
      -s, --storage-gbs INTEGER  Root disk size in GBs. Defaults to 8.
      -i, --instance-type TEXT   AWS instance type. Defaults to t2.micro.
      --help                     Show this message and exit.


## How it works
It takes your AWS credentials from your `~/.aws/credentials` file, and creates a keypair, then a security group and then all the VMs for your cluster. There's lot of work which can be done to make this project a seamless experience. For example, we can have support for AWS 'profiles', by specifying `--profile my-personal-aws-acct-credentials`.

## Goal

This project aims to create a CLI tool to quickly create clusters in a cloud. There's no such well-defined automation for a lot of clustered, distributed systems like Cassandra, Apache Kafka, Apache Spark, MongoDB, Riak, apache Storm, etc. and this projects aims to bridge that gap. In future, we should have support for multiple cloud providers -- both hypervisor and container based. Contributions welcome!
