import plyvel
from stat import *
from ethereum_freezer_tables import FreezerBodiesTable, FreezerHashesTable, FreezerHeadersTable


chaindata = "/home/drgrid/.ethereum/geth/chaindata"
ancient_chaindata_path = "/home/drgrid/.ethereum/geth/chaindata/ancient"
db = plyvel.DB(chaindata, compression=None)

def header_hash_key(number: int) -> bytes:
    return bytes("h", "ascii") + number.to_bytes(8, "big") + bytes("n", "ascii")

def block_body_key(number: int, hash: bytes) -> bytes:
    return bytes("b", "ascii") + number.to_bytes(8, "big") + hash

print(header_hash_key(1000))

print(db.get(bytes("DatabaseVersion", "ascii")))
print(db.get(bytes("LastHeader", "ascii")))
print(db.get(bytes("LastBlock", "ascii")))
print(db.get(header_hash_key(1000)))


# Example for an RLP object
class DBReader:
    def __init__(self):
        # block 46147 has the first transaction
        freezer_hash_table = FreezerHashesTable(ancient_chaindata_path)
        hash = freezer_hash_table.get_hash_by_height(46147)
        print("result: ", hash)
        print("length:", len(hash))
        print("results hex: ", hash.hex())

        freezer_bodies_table = FreezerBodiesTable(ancient_chaindata_path)
        body = freezer_bodies_table.get_body_by_height(46147)
        print("decoded body:", body)
        print("body from db:", db.get(block_body_key(46147, hash)))

        tx = body.Transactions[0]
        print("custom decoded tx:", tx)
        print("transaction hash:", tx.hash().hex())

        freezer_headers_table = FreezerHeadersTable(ancient_chaindata_path)
        header = freezer_headers_table.get_header_by_height(46147)
        print("decoded header:", header)

reader = DBReader()









