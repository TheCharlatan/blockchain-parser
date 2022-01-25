import os
from blockchain_parser.blockchain import Blockchain
from detectors import gnu_strings, find_file_with_imghdr
import sqlite3
import enum
import bitcoin.rpc
import binascii


def unhexlify_str(h: str) -> bytes:
    return binascii.unhexlify(h.encode('ascii'))


class COIN(enum.Enum):
    """ Coin/Blockchain """

    BITCOIN_MAINNET = "bitcoin_mainnet"
    BITCOIN_TESTNET3 = "bitcoin_testnet3"
    BITCOIN_REGTEST = "bitcoin_regtest"
    MONERO_MAINNET = "monero_mainnet"
    MONERO_STAGENET = "monero_stagnet"
    MONERO_TESTNET = "monero_testnet"


class DATATYPE(enum.Enum):
    """ Transaction Data Fields """

    SCRIPT_SIG = "scriptsig"  # input transaction data
    SCRIPT_PUBKEY = "script_pubkey"  # output transaction data
    TX_EXTRA = "tx_extra"


def setup_db() -> sqlite3.Connection:
    """ Create a new database if one does not exist already."""
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
    """Insert a new record into the database."""
    conn.execute(
        "INSERT INTO cryptoData(DATA,TXID,COIN,DATA_TYPE,BLOCK_HEIGHT,EXTRA_INDEX) values(?,?,?,?,?,?)", (data, txid, coin.value, data_type.value, block_height, extra_index))


def get_records(conn: sqlite3.Connection, txid: str, extra_index: int) -> None:
    """Print all the records in the database."""
    c = conn.cursor()
    c.execute(
        "SELECT * FROM  cryptoData WHERE txid=? AND extra_index=?", (txid,
                                                                     extra_index)
    )
    result = c.fetchall()
    print(result)


conn = setup_db()


def detect_op_return_output(script: bitcoin.core.script.CScript) -> bool:
    """Return true if the script contains the OP_RETURN opcode."""
    for elem in script.raw_iter():
        for code in elem:
            if code == bitcoin.core.script.OP_RETURN:
                return True
    return False


def bitcoin_find_file_with_imghdr(script: bitcoin.core.CScript) -> str:
    # try finding a file in the full script
    res = find_file_with_imghdr(script)
    if res:
        return res
    for op in script:
        # ignore single op codes
        if type(op) is int:
            continue
        # try finding a file in one of the script arguments
        res = find_file_with_imghdr(op)
        if res:
            return res
    return ''


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
            detected_file = find_file_with_imghdr(input.scriptSig)
            if len(detected_file) > 0:
                insert_record(conn, input.scriptSig, tx.txid, COIN.BITCOIN_REGTEST,
                              DATATYPE.SCRIPT_SIG, block.height, index)
                continue

            detected_text = gnu_strings(input.scriptSig, 4)
            if detected_text:
                insert_record(conn, input.scriptSig, tx.txid,
                              COIN.BITCOIN_REGTEST, DATATYPE.SCRIPT_SIG, block.height, index)


c = conn.cursor()
c.execute("SELECT data FROM cryptoData WHERE data_type=?",
          (DATATYPE.SCRIPT_SIG.value, ))
results = c.fetchall()
for result in results:
    for potential_string in result:
        print(gnu_strings(potential_string))
        print(bitcoin_find_file_with_imghdr(
            bitcoin.core.CScript(potential_string)))
