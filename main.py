from binascii import unhexlify
import os
from blockchain_parser.blockchain import Blockchain
import sqlite3
import enum
import bitcoin.rpc
import binascii


def unhexlify_str(h: str) -> bytes:
    return binascii.unhexlify(h.encode('ascii'))


class COIN(enum.Enum):
    """ Coin/Blockchain """

    BITCOIN_MAINNET = "bitcoin mainnet"
    BITCOIN_TESTNET3 = "bitcoin testnet3"
    BITCOIN_REGTEST = "bitcoin regtest"


class DATATYPE(enum.Enum):
    """ Transaction Data Fields """

    SCRIPT_SIG = "scriptsig"  # input transaction data
    SCRIPT_PUBKEY = "script pubkey"  # output transaction data


def setup_db() -> sqlite3.Connection:
    conn = sqlite3.connect('test.db')
    c = conn.cursor()
    c.execute(
        ''' SELECT count(name) FROM sqlite_master WHERE type='table' AND name='cryptoData' ''')
    if c.fetchone()[0] == 1:
        print('Table already exists.')
    else:
        c.execute('''CREATE TABLE cryptoData(
            DATA TEXT NOT NULL,
            TXID CHAR(64) NOT NULL,
            COIN TEXT NOT NULL,
            DATA_TYPE TEXT NOT NULL,
            EXTRA_INDEX INTEGER,
            PRIMARY KEY (TXID, EXTRA_INDEX),
            UNIQUE(TXID, EXTRA_INDEX)
        );''')

        print("Table successfully created")
    return conn


def insert_record(conn: sqlite3.Connection, data: str, txid: str, coin: COIN, data_type: DATATYPE, extra_index: int) -> None:
    conn.execute(
        "INSERT INTO cryptoData(DATA,TXID,COIN,DATA_TYPE,EXTRA_INDEX) values(?,?,?,?,?)", (data, txid, coin.value, data_type.value, extra_index))


def get_records(conn: sqlite3.Connection, txid: str, extra_index: int) -> None:
    c = conn.cursor()
    c.execute(
        "SELECT * FROM  cryptoData WHERE txid=? AND extra_index=?", (txid,
                                                                     extra_index)
    )
    result = c.fetchall()
    print(result)


conn = setup_db()
# get_records(conn, 'txid_0', 0)


def detect_op_return_output(script: bitcoin.core.script.CScript) -> bool:
    for elem in script.raw_iter():
        for code in elem:
            if code == bitcoin.core.script.OP_RETURN:
                return True
    return False


# To get the blocks ordered by height, you need to provide the path of the
# `index` directory (LevelDB index) being maintained by bitcoind. It contains
# .ldb files and is present inside the `blocks` directory.
blockchain = Blockchain(os.path.expanduser(
    '~/.bitcoin/regtest/blocks'))
for block in blockchain.get_ordered_blocks(os.path.expanduser('~/.bitcoin/regtest/blocks/index'), end=1000):
    for tx in block.transactions:
        c_tx = bitcoin.core.CTransaction.deserialize(tx.hex)
        # do some simple OP_RETURN detection
        for (index, out) in enumerate(c_tx.vout):
            if detect_op_return_output(out.scriptPubKey):
                # print("\nOP RETURN FOUND", out)
                insert_record(conn, out.scriptPubKey, tx.txid,
                              COIN.BITCOIN_REGTEST, DATATYPE.SCRIPT_PUBKEY, index)
        # for (index, input) in enumerate(c_tx.vin):
            # print(input, block.height)


test_string = "004d7273206475636b206973207665727920636f6e6365726e65642c207665727920636f6e6365726e65642e00"
text_bytes = unhexlify(test_string)
print(text_bytes.decode("ascii"))


c = conn.cursor()
c.execute("SELECT * FROM cryptoData")
result = c.fetchall()
# print(result)
