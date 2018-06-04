
from modules.muzika_contract import MuzikaContract


class MuzikaPaperContract(MuzikaContract):
    __contract_name__ = 'MuzikaPaperContract'

    def __init__(self, web3, *args, **kwargs):
        super(MuzikaPaperContract, self).__init__(web3, *args, **kwargs)

    def purchased(self, wallet_address, tx_data=None):
        """
        Return whether the wallet purchased this paper or not
        :param wallet_address: wallet address to check
        :param tx_data: transaction params to call function
        :return: True if wallet purchased, nor false if not
        """
        return self.contract.functions.isPurchased(wallet_address).call(tx_data)

    def is_sold_out(self, tx_data=None):
        """
        Return whether this paper is sold out, so cannot buy it.
        :param tx_data: transaction params to call function
        :return: True if sold out, nor false if not
        """
        return self.contract.functions.forSale().call(tx_data)

    def get_seller(self, tx_data=None):
        """
        Return the seller's wallet address.
        :return: seller's wallet address
        """
        return self.contract.functions.seller().call(tx_data)

    def generate(self, seller, price, ipfs_file_hash, original_file_hash):
        return super(MuzikaPaperContract, self).generate(seller, price, ipfs_file_hash, original_file_hash)
