FROM ubuntu:latest
MAINTAINER Muzika <official@muzika.network>

RUN apt-get update
RUN export DEBIAN_FRONTEND=noninteractive && apt-get install tzdata
RUN apt-get install -y git python3 python3-pip wget zip awscli npm nodejs
RUN wget https://dist.ipfs.io/go-ipfs/v0.4.15/go-ipfs_v0.4.15_linux-386.tar.gz
RUN tar xvfz go-ipfs_v0.4.15_linux-386.tar.gz
RUN mv go-ipfs/ipfs /usr/local/bin/ipfs
RUN npm install -g ganache-cli truffle
