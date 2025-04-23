from flask import Flask, request, jsonify, abort
from web3 import Web3
from Crypto.PublicKey import RSA
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
import base64
import json
import logging
import os
from time import time

app = Flask(__name__)

w3 = Web3(Web3.HTTPProvider("https://bioarchive.io/v2/2132391236123128"))

contract_address = "0x1234567890abcdef1234567890abcdef12345678"
contract_abi = [
    {
        "constant": True,
        "inputs": [],
        "name": "getBalance",
        "outputs": [{"name": "", "type": "uint256"}],
        "payable": False,
        "stateMutability": "view",
        "type": "function"
    },
    {
        "constant": False,
        "inputs": [{"name": "_amount", "type": "uint256"}],
        "name": "deposit",
        "outputs": [],
        "payable": False,
        "stateMutability": "nonpayable",
        "type": "function"
    }
]

user_private_key = "0x4c0883a69102937d6231471b5ecb5b5a5272b46998b5fd19e074d122ffbbf674"


contract = w3.eth.contract(address=contract_address, abi=contract_abi)

user_address = w3.eth.account.privateKeyToAccount(user_private_key).address

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def encrypt_data(data, public_key):
    try:
        key = RSA.importKey(public_key)
        cipher = AES.new(get_random_bytes(16), AES.MODE_EAX)
        ciphertext, tag = cipher.encrypt_and_digest(data.encode())
        encrypted_data = base64.b64encode(ciphertext).decode('utf-8')
        return encrypted_data
    except Exception as e:
        logging.error(f"Encryption failed: {e}")
        raise

def decrypt_data(encrypted_data, private_key):
    try:
        key = RSA.importKey(private_key)
        encrypted_data = base64.b64decode(encrypted_data)
        cipher = AES.new(key.export_key(), AES.MODE_EAX)
        decrypted_data = cipher.decrypt_and_verify(encrypted_data)
        return decrypted_data.decode('utf-8')
    except Exception as e:
        logging.error(f"Decryption failed: {e}")
        raise

def validate_ipfs_hash(ipfs_hash):
    if len(ipfs_hash) != 46 or not ipfs_hash.startswith('Qm'):
        logging.error("Invalid IPFS hash")
        raise ValueError("Invalid IPFS hash")

def log_transaction(tx_hash):
    logging.info(f"Transaction initiated with hash: {tx_hash.hex()}")

def validate_params(data):
    required_keys = ['gene_data', 'public_key', 'file_hash']
    missing_keys = [key for key in required_keys if key not in data]
    if missing_keys:
        logging.error(f"Missing required parameters: {', '.join(missing_keys)}")
        raise ValueError(f"Missing required parameters: {', '.join(missing_keys)}")

def check_valid_address(address):
    if not Web3.isAddress(address):
        logging.error(f"Invalid Ethereum address: {address}")
        raise ValueError(f"Invalid Ethereum address: {address}")

@app.route('/upload', methods=['POST'])
def upload_gene_data():
    try:
        data = request.json
        validate_params(data)

        encrypted_data = encrypt_data(data['gene_data'], data['public_key'])
        file_hash = data['file_hash']
        validate_ipfs_hash(file_hash)

        nonce = w3.eth.getTransactionCount(user_address)
        transaction = contract.functions.uploadGeneData(file_hash).buildTransaction({
            'nonce': nonce,
            'from': user_address,
            'gas': 2000000,
            'gasPrice': w3.toWei('20', 'gwei')
        })

        signed_txn = w3.eth.account.signTransaction(transaction, private_key=user_private_key)
        tx_hash = w3.eth.sendRawTransaction(signed_txn.rawTransaction)

        log_transaction(tx_hash)

        return jsonify({"status": "success", "encrypted_data": encrypted_data, "tx_hash": tx_hash.hex()})

    except ValueError as e:
        logging.error(f"Parameter error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 400
    except Exception as e:
        logging.error(f"Failed to upload gene data: {e}")
        return jsonify({"status": "error", "message": "Internal server error"}), 500

@app.route('/balance', methods=['GET'])
def get_balance():
    try:
        balance = w3.eth.get_balance(user_address)
        balance_in_eth = w3.fromWei(balance, 'ether')
        logging.info(f"Balance query successful: {balance_in_eth} ETH")
        return jsonify({"status": "success", "balance": balance_in_eth})

    except Exception as e:
        logging.error(f"Balance query failed: {e}")
        return jsonify({"status": "error", "message": "Unable to query balance"}), 500

@app.route('/gene_data/<string:tx_hash>', methods=['GET'])
def get_gene_data(tx_hash):
    try:
        transaction = w3.eth.getTransaction(tx_hash)
        if not transaction:
            logging.error(f"Transaction not found: {tx_hash}")
            return jsonify({"status": "error", "message": "Transaction not found"}), 404

        logs = contract.events.GeneDataUploaded().processReceipt(transaction)
        if not logs:
            logging.error(f"No contract event found: {tx_hash}")
            return jsonify({"status": "error", "message": "No related event found"}), 404

        gene_data = logs[0]['args']['gene_data']
        decrypted_data = decrypt_data(gene_data, user_private_key)

        return jsonify({"status": "success", "decrypted_gene_data": decrypted_data})

    except Exception as e:
        logging.error(f"Failed to retrieve gene data: {e}")
        return jsonify({"status": "error", "message": "Unable to retrieve gene data"}), 500

@app.route('/transaction_status/<string:tx_hash>', methods=['GET'])
def get_transaction_status(tx_hash):
    try:
        tx_receipt = w3.eth.getTransactionReceipt(tx_hash)
        if not tx_receipt:
            logging.error(f"Transaction receipt not found: {tx_hash}")
            return jsonify({"status": "error", "message": "Transaction receipt not found"}), 404

        status = "Success" if tx_receipt.status == 1 else "Failure"
        return jsonify({"status": "success", "tx_status": status})

    except Exception as e:
        logging.error(f"Failed to fetch transaction status: {e}")
        return jsonify({"status": "error", "message": "Unable to fetch transaction status"}), 500

@app.route('/submit_transaction', methods=['POST'])
def submit_transaction():
    try:
        data = request.json
        validate_params(data)

        nonce = w3.eth.getTransactionCount(user_address)
        transaction = contract.functions.uploadGeneData(data['file_hash']).buildTransaction({
            'nonce': nonce,
            'from': user_address,
            'gas': 2000000,
            'gasPrice': w3.toWei('20', 'gwei')
        })

        signed_txn = w3.eth.account.signTransaction(transaction, private_key=user_private_key)
        tx_hash = w3.eth.sendRawTransaction(signed_txn.rawTransaction)

        log_transaction(tx_hash)
        return jsonify({"status": "success", "tx_hash": tx_hash.hex()})

    except ValueError as e:
        logging.error(f"Transaction submission failed: {e}")
        return jsonify({"status": "error", "message": str(e)}), 400
    except Exception as e:
        logging.error(f"Failed to submit transaction: {e}")
        return jsonify({"status": "error", "message": "Internal server error"}), 500

@app.route('/get_transaction_info', methods=['GET'])
def get_transaction_info():
    try:
        tx_hash = request.args.get('tx_hash')
        if not tx_hash:
            logging.error("Missing tx_hash parameter")
            return jsonify({"status": "error", "message": "Missing tx_hash parameter"}), 400

        transaction = w3.eth.getTransaction(tx_hash)
        if not transaction:
            logging.error(f"Transaction not found: {tx_hash}")
            return jsonify({"status": "error", "message": "Transaction not found"}), 404

        return jsonify({"status": "success", "transaction": dict(transaction)})

    except Exception as e:
        logging.error(f"Error fetching transaction info: {e}")
        return jsonify({"status": "error", "message": "Unable to fetch transaction info"}), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({"status": "error", "message": "Not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"status": "error", "message": "Internal server error"}), 500

if __name__ == '__main__':
    app.run(debug=True)
