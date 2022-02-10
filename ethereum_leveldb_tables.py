from typing import Optional
import plyvel

# headerHashKey = headerPrefix + num (uint64 big endian) + headerHashSuffix
def header_hash_key(number: int) -> bytes:
    return bytes("h", "ascii") + number.to_bytes(8, "big") + bytes("n", "ascii")

# blockBodyKey = blockBodyPrefix + num (uint64 big endian) + hash
def block_body_key(number: int, hash: bytes) -> bytes:
    return bytes("b", "ascii") + number.to_bytes(8, "big") + hash

# headerKey = headerPrefix + num (uint64 big endian) + hash 
def header_key(number: int, hash: bytes) -> bytes:
    return bytes("h", "ascii") + number.to_bytes(8, "big") + hash


class EthLevelDB:
    def __init__(self, chaindata_path: str):
        self.chaindata_path = chaindata_path
        self.db = plyvel.DB(chaindata_path, compression=None)
    
    def get_hash_by_height(self, number: int) -> Optional[bytes]:
        return self.db.get(header_hash_key(number))

    def get_body_by_height(self, number: int) -> Optional[bytes]:
        header = self.db.get(header_hash_key(number))
        if header is None:
            return
        return self.db.get(block_body_key(number))
    
    def get_header_by_height(self, number: int) -> Optional[bytes]:
        header = self.db.get(header_hash_key(number))
        if header is None:
            return
        return self.db.get(header_key(number))

