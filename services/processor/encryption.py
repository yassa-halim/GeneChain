from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import os
import hashlib

class DataEncryption:
    def __init__(self, encryption_key: bytes):
        self.encryption_key = encryption_key

    def encrypt_data(self, data: str) -> bytes:
        iv = os.urandom(16)
        cipher = Cipher(algorithms.AES(self.encryption_key), modes.CBC(iv), backend=default_backend())
        encryptor = cipher.encryptor()
        padded_data = self._pad_data(data.encode('utf-8'))
        encrypted_data = encryptor.update(padded_data) + encryptor.finalize()
        return iv + encrypted_data

    def decrypt_data(self, encrypted_data: bytes) -> str:
        iv = encrypted_data[:16]
        cipher = Cipher(algorithms.AES(self.encryption_key), modes.CBC(iv), backend=default_backend())
        decryptor = cipher.decryptor()
        decrypted_data = decryptor.update(encrypted_data[16:]) + decryptor.finalize()
        return self._unpad_data(decrypted_data).decode('utf-8')

    def _pad_data(self, data: bytes) -> bytes:
        padding_length = 16 - len(data) % 16
        return data + bytes([padding_length] * padding_length)

    def _unpad_data(self, data: bytes) -> bytes:
        padding_length = data[-1]
        return data[:-padding_length]

    def sign_data(self, data: str) -> str:
        return hashlib.sha256(data.encode('utf-8')).hexdigest()

    def verify_signature(self, data: str, signature: str) -> bool:
        return self.sign_data(data) == signature
