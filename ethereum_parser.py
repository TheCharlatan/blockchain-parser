import plyvel
from stat import *
from ethereum_blockchain_iterator import ParseEthereumBlockBodies, ParseEthereumBlockHeaders
from ethereum_freezer_tables import FreezerBodiesTable, FreezerHashesTable, FreezerHeadersTable


chaindata_path = "/home/drgrid/.ethereum/geth/chaindata"
ancient_chaindata_path = "/home/drgrid/.ethereum/geth/chaindata/ancient"

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

        tx = body.Transactions[0]
        print("custom decoded tx:", tx)
        print("transaction hash:", tx.hash().hex())

        freezer_headers_table = FreezerHeadersTable(ancient_chaindata_path)
        header = freezer_headers_table.get_header_by_height(46147)
        print("decoded header:", header)

        for i, j in enumerate(ParseEthereumBlockBodies(ancient_chaindata_path, chaindata_path)):
            print(i, j)

        for i, j in enumerate(ParseEthereumBlockHeaders(ancient_chaindata_path, chaindata_path)):
           print(i, j)


reader = DBReader()

