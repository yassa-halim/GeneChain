from web3 import Web3
import json

class SmartContractManager:
    def __init__(self, blockchain_url: str, contract_address: str, abi: str):
        self.web3 = Web3(Web3.HTTPProvider(blockchain_url))
        self.contract_address = contract_address
        self.abi = json.loads(abi)
        self.contract = self.web3.eth.contract(address=self.contract_address, abi=self.abi)

    def deploy_contract(self, contract_name: str, args: list, gas_limit: int) -> str:
        contract_bytecode = self.get_contract_bytecode(contract_name)
        contract_abi = self.get_contract_abi(contract_name)
        contract = self.web3.eth.contract(abi=contract_abi, bytecode=contract_bytecode)
        deploy_txn = contract.constructor(*args).buildTransaction({
            'from': self.web3.eth.accounts[0],
            'gas': gas_limit,
            'gasPrice': self.web3.toWei('20', 'gwei'),
            'nonce': self.web3.eth.getTransactionCount(self.web3.eth.accounts[0]),
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

    def interact_with_contract(self, contract_function: str, params: list) -> dict:
        contract_function = self.contract.get_function_by_name(contract_function)(*params)
        tx = contract_function.buildTransaction({
            'from': self.web3.eth.accounts[0],
            'gas': 2000000,
            'gasPrice': self.web3.toWei('20', 'gwei'),
            'nonce': self.web3.eth.getTransactionCount(self.web3.eth.accounts[0]),
        })
        signed_tx = self.web3.eth.account.signTransaction(tx, private_key="your_private_key")
        tx_hash = self.web3.eth.sendRawTransaction(signed_tx.rawTransaction)
        return self.web3.toHex(tx_hash)

    def get_contract_data(self, contract_function: str, params: list) -> dict:
        contract_function = self.contract.get_function_by_name(contract_function)(*params)
        return contract_function.call()
