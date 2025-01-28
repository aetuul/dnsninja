import base64
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from Crypto.Random import get_random_bytes


def encrypt_message(plaintext, secret):
    """Encrypt a message using AES."""
    iv = get_random_bytes(16)  # Generate a random IV
    cipher = AES.new(secret, AES.MODE_CBC, iv)
    ciphertext = cipher.encrypt(pad(plaintext.encode(), AES.block_size))
    return base64.b64encode(iv + ciphertext).decode()

def decrypt_message(ciphertext, secret):
    """Decrypt a message using AES."""
    data = base64.b64decode(ciphertext)
    iv = data[:16]  # Extract the IV
    encrypted_data = data[16:]
    cipher = AES.new(secret, AES.MODE_CBC, iv)
    return unpad(cipher.decrypt(encrypted_data), AES.block_size).decode()
