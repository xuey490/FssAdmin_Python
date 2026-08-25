import base64
import hashlib
import os

import bcrypt
from cryptography.hazmat.backends.openssl import backend
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

_PBKDF2_ALGO = "sha256"
_PBKDF2_ITERATIONS = 600_000
_PBKDF2_SALT_LEN = 16
_PBKDF2_PREFIX = "$pbkdf2-sha256$"


class PwdUtil:
    """密码工具：新建用 bcrypt；校验兼容 PHP $2y$ 与历史 pbkdf2。"""

    @staticmethod
    def hash_password(password: str) -> str:
        hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=10))
        # 与 PHP password_hash 前缀一致，便于互通
        return hashed.decode("utf-8").replace("$2b$", "$2y$", 1)

    @staticmethod
    def verify_password(plain_password: str, password_hash: str) -> bool:
        if not password_hash:
            return False
        try:
            if password_hash.startswith("$2y$") or password_hash.startswith("$2a$") or password_hash.startswith("$2b$"):
                normalized = password_hash.replace("$2y$", "$2b$", 1).replace("$2a$", "$2b$", 1)
                return bcrypt.checkpw(plain_password.encode("utf-8"), normalized.encode("utf-8"))
            if password_hash.startswith(_PBKDF2_PREFIX):
                _, _algo, iters_str, salt_b64, hash_b64 = password_hash.split("$")
                salt = base64.b64decode(salt_b64)
                expected = base64.b64decode(hash_b64)
                dk = hashlib.pbkdf2_hmac(_PBKDF2_ALGO, plain_password.encode(), salt, int(iters_str))
                return dk == expected
        except Exception:
            return False
        return False

    @staticmethod
    def check_password_strength(password: str) -> str | None:
        if len(password) < 6:
            return "密码长度至少6位"
        return None


class AESCipher:
    def __init__(self, key: bytes | str) -> None:
        self.key = key if isinstance(key, bytes) else bytes.fromhex(key)

    def encrypt(self, plaintext: bytes | str) -> bytes:
        if not isinstance(plaintext, bytes):
            plaintext = str(plaintext).encode("utf-8")
        iv = os.urandom(16)
        cipher = Cipher(algorithms.AES(self.key), modes.CBC(iv), backend=backend)
        encryptor = cipher.encryptor()
        padder = padding.PKCS7(cipher.algorithm.block_size).padder()  # type: ignore
        padded_plaintext = padder.update(plaintext) + padder.finalize()
        ciphertext = encryptor.update(padded_plaintext) + encryptor.finalize()
        return iv + ciphertext

    def decrypt(self, ciphertext: bytes | str) -> str:
        ciphertext = ciphertext if isinstance(ciphertext, bytes) else bytes.fromhex(ciphertext)
        iv = ciphertext[:16]
        ciphertext = ciphertext[16:]
        cipher = Cipher(algorithms.AES(self.key), modes.CBC(iv), backend=backend)
        decryptor = cipher.decryptor()
        unpadder = padding.PKCS7(cipher.algorithm.block_size).unpadder()  # type: ignore
        padded_plaintext = decryptor.update(ciphertext) + decryptor.finalize()
        plaintext = unpadder.update(padded_plaintext) + unpadder.finalize()
        return plaintext.decode("utf-8")


class Md5Cipher:
    @staticmethod
    def encrypt(plaintext: bytes | str) -> str:
        md5 = hashlib.md5()
        if not isinstance(plaintext, bytes):
            plaintext = str(plaintext).encode("utf-8")
        md5.update(plaintext)
        return md5.hexdigest()
