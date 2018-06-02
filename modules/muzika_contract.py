
import json
import os

from config import MuzikaContractConfig

__all__ = [
    'MuzikaContractHandler'
]


def load_contract(contract_name, contract_dir=None):
    """
    loads a contract from json file.
    """
    # if the contract directory is None,
    # it loads the directory path from config.py
    if contract_dir is None:
        contract_dir = MuzikaContractConfig.build_path
    full_path = os.path.join(contract_dir, contract_name + '.json')
    # open the file and return as dict
    with open(full_path) as contract:
        return json.loads(contract.read())


class MuzikaContractHandler:
    """
    helps to create contracts for muzika.
    """
    __muzika_contract_interface__ = {
        'MuzikaPaperContract': load_contract('MuzikaPaperContract'),
        'MuzikaCoin': load_contract('MuzikaCoin'),
    }

    def __init__(self):
        pass

    def get_interface(self, contract_name):
        """
        Returns a contract interface
        """
        return self.__muzika_contract_interface__.get(contract_name, None)

    def get_contract_parameter(self, contract_name, address=None):
        """
        Create a dict for web3.eth.contract parameter.

        ex) MuzikaPaperContract
        >>> contract_handler = MuzikaContractHandler()
        >>> web3.eth.contract(**contract_handler.get_contract_parameter('MuzikaPaperContract'))
        """
        contract_interface = self.get_interface(contract_name)
        if contract_interface:
            ret = dict(abi=contract_interface['abi'])
            if address:
                ret.update({'address': address})
            return ret
        else:
            return None

    def get_contract(self, web3, contract_name, address=None):
        """
        Returns a contract.
        """
        return web3.eth.contract(**self.get_contract_parameter(contract_name, address=address))


class MuzikaContract(object):

    # child class of this class must define contract name
    __contract_name__ = ''
    contract = None

    def __init__(self, web3, *args, **kwargs):
        self.contract_address = kwargs.get('contract_address')
        contract_handler = MuzikaContractHandler()
        self.web3 = web3
        self.contract = contract_handler.get_contract(web3, self.__contract_name__, address=self.contract_address)

    def generate(self, *args, **kwargs):
        return self.contract.constructor(*args, **kwargs).transact()