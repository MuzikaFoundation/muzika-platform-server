
"""
 This script coverts linked string in bytecode in compiled contracts json file.
"""

import argparse
import glob
import json
import os
import re

import sys
sys.path.append('..')
from modules.web3 import get_web3

# define link
linker = {
    'LibPaperPaymentInterface': 'LibPaperPayment'
}


def load_contract(file_path):
    with open(file_path) as json_file:
        contract = json.loads(json_file.read())
        return contract


def contract_name_to_bytecode_string(contract_name):
    return ''.join(['__', contract_name, '_' * (38 - len(contract_name))])


def get_contract_name(contract_interface):
    return contract_interface['contractName']


def get_bytecode(contract_interface):
    return contract_interface['bytecode']


def get_deployed_bytecode(contract_interface):
    return contract_interface['deployedBytecode']


def get_address(contract_interface, network_protocol_version):
    return contract_interface['networks'][network_protocol_version]['address'][2:]


if __name__ == '__main__':
    args = argparse.ArgumentParser()
    args.add_argument('-d', '--directory', help='directory that has the truffle contract json file')
    args.add_argument('-r', '--recursive', help='Recursively search contract json file', required=False, default=False)
    args.add_argument('-n', '--version', help='Network protocol version', required=False)

    args = args.parse_args()

    if args.version:
        web3 = get_web3()
        network_version = web3.version.network
    else:
        network_version = args.version

    contracts_json = {}
    contracts_address = {}

    # load all contract json files
    for file_path in glob.glob(os.path.join(args.directory, '*'), recursive=args.recursive):
        # if not json file, ignore it
        _, ext = os.path.splitext(file_path)
        if ext != '.json':
            continue

        # get contract and contract address
        contract = load_contract(file_path)
        contract_name = get_contract_name(contract)
        try:
            contracts_json.update({contract_name: contract})
            contracts_address.update({contract_name: get_address(contract, network_version)})
        except KeyError:
            continue

    # link
    for key, item in linker.items():
        contracts_address[key] = contracts_address[item]

    # change strings in bytecode
    for file_path in glob.glob(os.path.join(args.directory, '*'), recursive=args.recursive):
        # if not json file, ignore it
        _, ext = os.path.splitext(file_path)
        if ext != '.json':
            continue

        # load json file and convert strings in bytecode
        with open(file_path, 'w') as file:
            path = os.path.basename(file_path)
            path, _ = os.path.splitext(path)
            contract_json = contracts_json[path]
            bytecode = contract_json['bytecode']
            deployed_bytecode = contract_json['deployedBytecode']

            for key, address in contracts_address.items():
                bytecode = bytecode.replace(contract_name_to_bytecode_string(key), address)
                deployed_bytecode = deployed_bytecode.replace(contract_name_to_bytecode_string(key), address)

            contract_json['bytecode'] = bytecode
            contract_json['deployedBytecode'] = deployed_bytecode
            # print(contract_json['bytecode'])

            file.write(json.dumps(contract_json))
