from rlp.sedes import (Serializable, List, BigEndianInt, Binary, binary, big_endian_int)
import rlp
from eth_hash.auto import keccak

address = Binary.fixed_length(20, allow_empty=True)
hash32 = Binary.fixed_length(32)
bloom = Binary.fixed_length(256)
uint32 = BigEndianInt(32)
uint256 = BigEndianInt(256)
int256 = BigEndianInt(256)
trie_root = Binary.fixed_length(32, allow_empty=True)

class Transaction(Serializable):
    """
    RLP object for transactions
    """
    fields = [
        ('nonce', big_endian_int),
        ('gasprice', big_endian_int),
        ('startgas', big_endian_int),
        ('to', address),
        ('value', big_endian_int),
        ('data', binary),
        ('v', big_endian_int),
        ('r', big_endian_int),
        ('s', big_endian_int),
    ]

    def __init__(self, nonce, gasprice, startgas, to, value, data, v=0, r=0, s=0, **kwargs):
        super().__init__(nonce, gasprice, startgas, to, value, data, v, r, s, **kwargs)
    
    def hash(self) -> bytes:
        return keccak(rlp.encode(self))



class Header(Serializable):
    """
    RLP object for headers
    """
    fields = [
        ('ParentHash', hash32),
        ('UncleHash', hash32),
        ('Coinbase', address),
        ('Root', trie_root),
        ('TxHash', trie_root),
        ('ReceiptHash', trie_root),
        ('Bloom', int256),
        ('Difficulty', big_endian_int),
        ('Number', big_endian_int),
        ('GasLimit', big_endian_int),
        ('GasUsed', big_endian_int),
        ('Time', big_endian_int),
        ('Extra', binary),
        ('MixDigest', binary),
        ('Nonce', binary)
    ]


class Body(Serializable):
    """
    RLP object for block bodies
    """
    fields = [
        ('Transactions', List([Transaction], False)),
        ('Uncles', List([Header], False))
    ]

