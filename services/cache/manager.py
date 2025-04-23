from .memory_classes.single_memory import SingleMemoryManager
import time
import hashlib
import json
from uuid import uuid4

class SingleMemoryManager:
    def __init__(self, memory_limit, eviction_k, storage_manager):
        self.memory_limit = memory_limit
        self.eviction_k = eviction_k
        self.storage_manager = storage_manager
        self.memory_store = {}

    def address_request(self, agent_request):
        if agent_request["action"] == "write":
            self.write_memory(agent_request["key"], agent_request["value"])
        elif agent_request["action"] == "read":
            return self.read_memory(agent_request["key"])
        elif agent_request["action"] == "delete":
            return self.delete_memory(agent_request["key"])
        elif agent_request["action"] == "update":
            return self.update_memory(agent_request["key"], agent_request["value"])

    def write_memory(self, key, value):
        if len(self.memory_store) >= self.memory_limit:
            self.evict_memory()
        self.memory_store[key] = {"value": value, "timestamp": time.time()}

    def read_memory(self, key):
        memory_entry = self.memory_store.get(key, None)
        if memory_entry:
            return memory_entry["value"]
        else:
            return None

    def delete_memory(self, key):
        if key in self.memory_store:
            del self.memory_store[key]

    def update_memory(self, key, value):
        if key in self.memory_store:
            self.memory_store[key]["value"] = value
            self.memory_store[key]["timestamp"] = time.time()
        else:
            self.write_memory(key, value)

    def evict_memory(self):
        if self.eviction_k == "LRU":
            self.evict_lru()
        elif self.eviction_k == "FIFO":
            self.evict_fifo()

    def evict_lru(self):
        if self.memory_store:
            oldest_key = min(self.memory_store, key=lambda k: self.memory_store[k]["timestamp"])
            del self.memory_store[oldest_key]

    def evict_fifo(self):
        if self.memory_store:
            first_key = next(iter(self.memory_store))
            del self.memory_store[first_key]

class Blockchain:
    def __init__(self, name="bioarchive"):
        self.name = name
        self.chain = []
        self.pending_transactions = []
        self.create_genesis_block()

    def create_genesis_block(self):
        genesis_block = {
            'index': 0,
            'timestamp': time.time(),
            'transactions': [],
            'previous_hash': "0",
            'hash': self.hash_block('0', [])
        }
        self.chain.append(genesis_block)

    def add_block(self, block_data):
        previous_block = self.chain[-1]
        block_data['index'] = len(self.chain)
        block_data['previous_hash'] = previous_block['hash']
        block_data['timestamp'] = time.time()
        block_data['hash'] = self.hash_block(block_data['previous_hash'], block_data['transactions'])
        self.chain.append(block_data)

    def hash_block(self, previous_hash, transactions):
        block_string = f"{previous_hash}{transactions}{time.time()}"
        return hashlib.sha256(block_string.encode()).hexdigest()

    def get_latest_block(self):
        return self.chain[-1]

    def validate_chain(self):
        for i in range(1, len(self.chain)):
            previous_block = self.chain[i - 1]
            current_block = self.chain[i]
            if current_block['previous_hash'] != previous_block['hash']:
                return False
            if self.hash_block(previous_block['hash'], current_block['transactions']) != current_block['hash']:
                return False
        return True

class User:
    def __init__(self, user_id, private_key, public_key):
        self.user_id = user_id
        self.private_key = private_key
        self.public_key = public_key
        self.data_access_permissions = {}

    def authorize_data_access(self, agent_id, access_level):
        self.data_access_permissions[agent_id] = access_level

class Data:
    def __init__(self, user_id, data_content):
        self.data_id = str(uuid4())
        self.user_id = user_id
        self.data_content = data_content
        self.timestamp = time.time()

    def encrypt_data(self, public_key):
        self.data_content = self._simple_encryption(self.data_content, public_key)

    def decrypt_data(self, private_key):
        self.data_content = self._simple_decryption(self.data_content, private_key)

    def _simple_encryption(self, data, key):
        return ''.join([chr(ord(c) + len(key)) for c in data])

    def _simple_decryption(self, data, key):
        return ''.join([chr(ord(c) - len(key)) for c in data])

class MemoryManager:
    def __init__(self, blockchain, memory_limit=1024):
        self.blockchain = blockchain
        self.memory_manager = SingleMemoryManager(memory_limit, eviction_k="LRU", storage_manager=None)

    def store_data(self, user, data_content):
        data = Data(user.user_id, data_content)
        data.encrypt_data(user.public_key)
        key = data.data_id
        self.memory_manager.write_memory(key, data.data_content)
        transaction = {
            'agent_id': user.user_id,
            'data_id': data.data_id,
            'action': 'store',
            'content': data.data_content
        }
        self.blockchain.add_block(transaction)

    def retrieve_data(self, user, data_id):
        data_content = self.memory_manager.read_memory(data_id)
        if data_content:
            data = Data(user.user_id, data_content)
            data.decrypt_data(user.private_key)
            return data
        else:
            raise ValueError("Data not found.")

    def update_data(self, user, data_id, new_data_content):
        self.memory_manager.update_memory(data_id, new_data_content)
        data = Data(user.user_id, new_data_content)
        data.encrypt_data(user.public_key)
        transaction = {
            'agent_id': user.user_id,
            'data_id': data.data_id,
            'action': 'update',
            'content': data.data_content
        }
        self.blockchain.add_block(transaction)

    def delete_data(self, user, data_id):
        self.memory_manager.delete_memory(data_id)
        transaction = {
            'agent_id': user.user_id,
            'data_id': data_id,
            'action': 'delete'
        }
        self.blockchain.add_block(transaction)

class BlockchainNetwork:
    def __init__(self):
        self.blockchain = Blockchain()
        self.users = {}
        self.memory_manager = MemoryManager(self.blockchain)

    def add_user(self, user):
        self.users[user.user_id] = user

    def perform_transaction(self, agent_request):
        user = self.users.get(agent_request["agent_id"])
        if user:
            if agent_request["action"] == "store":
                self.memory_manager.store_data(user, agent_request["content"])
            elif agent_request["action"] == "retrieve":
                return self.memory_manager.retrieve_data(user, agent_request["key"])
            elif agent_request["action"] == "update":
                self.memory_manager.update_data(user, agent_request["key"], agent_request["value"])
            elif agent_request["action"] == "delete":
                self.memory_manager.delete_data(user, agent_request["key"])
            else:
                raise ValueError("Unknown operation.")
        else:
            raise ValueError("User not found.")
