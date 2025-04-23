from web3 import Web3
import json

class DataStorage:
    def __init__(self, blockchain_url: str, contract_address: str, abi: str):
        self.web3 = Web3(Web3.HTTPProvider(blockchain_url))
        self.contract_address = contract_address
        self.abi = json.loads(abi)
        self.contract = self.web3.eth.contract(address=self.contract_address, abi=self.abi)

    def store_data_on_blockchain(self, data: str) -> str:
        tx = self.contract.functions.storeGeneData(data).buildTransaction({
            "from": self.web3.eth.accounts[0],
            "gas": 2000000,
            "gasPrice": self.web3.toWei('20', 'gwei'),
            "nonce": self.web3.eth.getTransactionCount(self.web3.eth.accounts[0]),
        })
        signed_tx = self.web3.eth.account.signTransaction(tx, private_key="your_private_key")
        tx_hash = self.web3.eth.sendRawTransaction(signed_tx.rawTransaction)
        return self.web3.toHex(tx_hash)

    def retrieve_data_from_blockchain(self, tx_hash: str) -> dict:
        tx_receipt = self.web3.eth.getTransactionReceipt(tx_hash)
        if tx_receipt["status"] == 1:
            logs = self.contract.events.GeneDataStored().processReceipt(tx_receipt)
            return logs[0]['args']
        else:
            raise Exception(f"Failed to retrieve data for tx_hash: {tx_hash}")

    def query_contract_data(self, function_name: str, params: list) -> dict:
        contract_function = self.contract.get_function_by_name(function_name)(*params)
        return contract_function.call()
