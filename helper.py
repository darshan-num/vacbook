import os
import hashlib


def create_hash(str_val):
    hash_val = hashlib.sha256()
    hash_val.update(bytes(str(str_val), 'utf-8'))
    return str(hash_val.hexdigest())


def alert():
    os.system("""afplay ./media/alert.mp3""")
