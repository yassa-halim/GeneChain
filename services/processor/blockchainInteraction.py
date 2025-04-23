from web3 import Web3
import json

class BlockchainInteraction:
    def __init__(self, blockchain_url: str, contract_address: str, abi: str):
        self.web3 = Web3(Web3.HTTPProvider(blockchain_url))
        self.contract_address = contract_address
        self.abi = json.loads(abi)
        self.contract = self.web3.eth.contract(address=self.contract_address, abi=self.abi)
        self.account = self.web3.eth.accounts[0]

    def store_data(self, data: str) -> str:
        tx = self.contract.functions.storeGeneData(data).buildTransaction({
            "from": self.account,
            "gas": 2000000,
            "gasPrice": self.web3.toWei('20', 'gwei'),
            "nonce": self.web3.eth.getTransactionCount(self.account),
        })
        signed_tx = self.web3.eth.account.signTransaction(tx, private_key="your_private_key")
        tx_hash = self.web3.eth.sendRawTransaction(signed_tx.rawTransaction)
        return self.web3.toHex(tx_hash)

    def get_data(self, tx_hash: str) -> dict:
        tx_receipt = self.web3.eth.getTransactionReceipt(tx_hash)
        if tx_receipt["status"] == 1:
            logs = self.contract.events.GeneDataStored().processReceipt(tx_receipt)
            return logs[0]['args']
        else:
            raise Exception(f"Failed to retrieve data for tx_hash: {tx_hash}")

    def get_transaction_status(self, tx_hash: str) -> str:
        tx_receipt = self.web3.eth.getTransactionReceipt(tx_hash)
        if tx_receipt:
            if tx_receipt['status'] == 1:
                return "Success"
            else:
                return "Failure"
        else:
            return "Pending"

    def get_contract_balance(self) -> str:
        return self.web3.fromWei(self.web3.eth.getBalance(self.contract_address), 'ether')

    def deploy_contract(self, contract_name: str, args: list, gas_limit: int) -> str:
        contract_bytecode = self.get_contract_bytecode(contract_name)
        contract_abi = self.get_contract_abi(contract_name)
        contract = self.web3.eth.contract(abi=contract_abi, bytecode=contract_bytecode)
        deploy_txn = contract.constructor(*args).buildTransaction({
            'from': self.account,
            'gas': gas_limit,
            'gasPrice': self.web3.toWei('20', 'gwei'),
            'nonce': self.web3.eth.getTransactionCount(self.account),
        })
        signed_tx = self.web3.eth.account.signTransaction(deploy_txn, private_key="your_private_key")
        tx_hash = self.web3.eth.sendRawTransaction(signed_tx.rawTransaction)
        return self.web3.toHex(tx_hash)

    def get_contract_bytecode(self, contract_name: str) -> str:
        with open(f'{contract_name}.bin', 'r') as file:
            return file.read()

    def get_contract_abi(self, contract_name: str) -> dict:
        with open(f'{contract_name}.abi', 'r') as file:
            return json.load(file)
