FROM ubuntu:latest
MAINTAINER Muzika <official@muzika.network>

RUN apt-get update
RUN apt-get install -y wget python3.6
RUN wget https://dist.ipfs.io/go-ipfs/v0.4.15/go-ipfs_v0.4.15_linux-386.tar.gz
RUN tar xvfz go-ipfs_v0.4.15_linux-386.tar.gz
RUN mv go-ipfs/ipfs /usr/local/bin/ipfs

EXPOSE 4001
EXPOSE 4002
EXPOSE 4004
