# <a href="quick-cluster.github.com">Quick Cluster</a>

Quickly and easily create a Cassandra cluster on EC2 cloud.


# Installation

Clone this repository, and run `python setup.py develop`

# Usage

Example:

    $ qc cassandra --nodes 5 --storage-gbs 100 --instance-type m4.large --region us-west-1

View all options:

    $ qc --help


## Goal

This project aims to create a CLI tool to quickly create clusters in a cloud. There's no such well-defined automation for a lot of clustered, distributed systems like Cassandra, Apache Kafka, Apache Spark, MongoDB, Riak, apache Storm, etc. and this projects aims to bridge that gap. In future, we should have support for multiple cloud providers -- both hypervisor and container based. Contributions welcome!
