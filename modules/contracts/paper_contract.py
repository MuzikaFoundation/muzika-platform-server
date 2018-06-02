
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
        # @TODO Should provide `from` because of lack of the web3.eth.accounts[0] in test and main network
        # So, Implement custom provider like provider engine or every call function should be provided with `from`
        return self.contract.functions.isPurchased(wallet_address).call({
            'from': '0x0000000000000000000000000000000000000000'
        })

    def is_sold_out(self):
        """
        Return whether this paper is sold out, so cannot buy it.
        :return: True if sold out, nor false if not
        """
        return self.contract.functions.soldOut().call()

    def get_seller(self):
        """
        Return the seller's wallet address.
        :return: seller's wallet address
        """
        return self.contract.functions.seller().call()

    def generate(self, seller, price, ipfs_file_hash, original_file_hash):
        return super(MuzikaPaperContract, self).generate(seller, price, ipfs_file_hash, original_file_hash)
