import subprocess
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
    if not c.fetchone()[0] == 1:
        c.execute('''CREATE TABLE cryptoData(
            DATA TEXT NOT NULL,
            TXID CHAR(64) NOT NULL,
            COIN TEXT NOT NULL,
            DATA_TYPE TEXT NOT NULL,
            BLOCK_HEIGHT INTEGER NOT NULL,
            EXTRA_INDEX INTEGER,
            PRIMARY KEY (TXID, EXTRA_INDEX, DATA_TYPE),
            UNIQUE(TXID, EXTRA_INDEX, DATA_TYPE)
        );''')

        print("Table successfully created")
    return conn


def insert_record(conn: sqlite3.Connection, data: str, txid: str, coin: COIN, data_type: DATATYPE, block_height: int, extra_index: int) -> None:
    conn.execute(
        "INSERT INTO cryptoData(DATA,TXID,COIN,DATA_TYPE,BLOCK_HEIGHT,EXTRA_INDEX) values(?,?,?,?,?,?)", (data, txid, coin.value, data_type.value, block_height, extra_index))


def get_records(conn: sqlite3.Connection, txid: str, extra_index: int) -> None:
    c = conn.cursor()
    c.execute(
        "SELECT * FROM  cryptoData WHERE txid=? AND extra_index=?", (txid,
                                                                     extra_index)
    )
    result = c.fetchall()
    print(result)


conn = setup_db()


def detect_op_return_output(script: bitcoin.core.script.CScript) -> bool:
    for elem in script.raw_iter():
        for code in elem:
            if code == bitcoin.core.script.OP_RETURN:
                return True
    return False


def find_string(bytestring: bytes, min: int = 10) -> str:
    cmd = "strings -n {}".format(min)
    process = subprocess.Popen(
        cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.PIPE)
    process.stdin.write(bytestring)
    output = process.communicate()[0]
    return output.decode("ascii").strip()


blockchain = Blockchain(os.path.expanduser(
    '~/.bitcoin/regtest/blocks'))
for block in blockchain.get_ordered_blocks(os.path.expanduser('~/.bitcoin/regtest/blocks/index'), end=1000):
    for tx in block.transactions:
        c_tx = bitcoin.core.CTransaction.deserialize(tx.hex)
        # do some simple OP_RETURN detection
        for (index, output) in enumerate(c_tx.vout):
            if detect_op_return_output(output.scriptPubKey):
                insert_record(conn, output.scriptPubKey, tx.txid,
                              COIN.BITCOIN_REGTEST, DATATYPE.SCRIPT_PUBKEY, block.height, index)
        for (index, input) in enumerate(c_tx.vin):
            detected_text = find_string(input.scriptSig)
            if detected_text:
                insert_record(conn, input.scriptSig, tx.txid,
                              COIN.BITCOIN_REGTEST, DATATYPE.SCRIPT_SIG, block.height, index)

c = conn.cursor()
c.execute("SELECT data FROM cryptoData WHERE data_type=?",
          (DATATYPE.SCRIPT_SIG.value, ))
results = c.fetchall()
for result in results:
    for potential_string in result:
        print(find_string(potential_string))
