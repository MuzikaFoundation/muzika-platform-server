
from modules.muzika_contract import MuzikaContract


class MuzikaPaperContract(MuzikaContract):
    __contract_name__ = 'MuzikaPaperContract'

    def __init__(self, web3, *args, **kwargs):
        super(MuzikaPaperContract, self).__init__(web3, *args, **kwargs)

    def purchased(self, wallet_address):
        """
        Return whether the wallet purchased this paper or not
        :param wallet_address: wallet address to check
        :return: True if wallet purchased, nor false if not
        """
        return self.contract.functions.isPurchased(wallet_address).call()

    def generate(self, seller, price, ipfs_file_hash, original_file_hash):
        return super(MuzikaPaperContract, self).generate(seller, price, ipfs_file_hash, original_file_hash)
