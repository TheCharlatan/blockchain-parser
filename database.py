import enum
import sqlite3
from typing import List


class COIN(enum.Enum):
    """Coin/Blockchain"""

    BITCOIN_MAINNET = "bitcoin_mainnet"
    BITCOIN_TESTNET3 = "bitcoin_testnet3"
    BITCOIN_REGTEST = "bitcoin_regtest"
    MONERO_MAINNET = "monero_mainnet"
    MONERO_STAGENET = "monero_stagnet"
    MONERO_TESTNET = "monero_testnet"
    ETHEREUM_MAINNET = "ethereum_mainnet"


def coinStringToCoin(name: str) -> COIN:
    if name == "bitcoin_mainnet":
        return COIN.BITCOIN_MAINNET
    elif name == "bitcoin_testnet3":
        return COIN.BITCOIN_TESTNET3
    elif name == "bitcoin_regtest":
        return COIN.BITCOIN_REGTEST
    elif name == "monero_mainnet":
        return COIN.MONERO_MAINNET
    elif name == "monero_stagenet":
        return COIN.MONERO_STAGENET
    elif name == "monero_testnet":
        return COIN.MONERO_TESTNET
    elif name == "ethereum_mainnet":
        return COIN.ETHEREUM_MAINNET
    else:
        raise "invalid coin name"


class DATATYPE(enum.Enum):
    """Transaction Data Fields"""

    SCRIPT_SIG = "scriptsig"  # input transaction data
    SCRIPT_PUBKEY = "script_pubkey"  # output transaction data
    TX_EXTRA = "tx_extra"
    TX_DATA = "tx_data"


class LABEL(enum.Enum):
    """Default Data labels"""

    OP_RETURN = "opreturn"
    TEXT = "text"
    IMAGE = "image"


class Database:
    def __init__(self, name: str) -> None:
        self.name = name
        conn = sqlite3.connect(self.name)
        c = conn.cursor()
        c.execute(
            """ SELECT count(name) FROM sqlite_master WHERE type='table' AND name='cryptoData' """
        )
        if not c.fetchone()[0] == 1:
            c.execute(
                """CREATE TABLE cryptoData(
                DATA TEXT NOT NULL,
                TXID CHAR(64) NOT NULL,
                COIN TEXT NOT NULL,
                DATA_TYPE TEXT NOT NULL,
                BLOCK_HEIGHT INTEGER NOT NULL,
                EXTRA_INDEX INTEGER,
                PRIMARY KEY (TXID, EXTRA_INDEX, DATA_TYPE),
                UNIQUE(TXID, EXTRA_INDEX, DATA_TYPE)
            );"""
            )

            print("Table successfully created")

        conn.commit()
        conn.close()

    def insert_records(
        self,
        records,
    ):
        conn = sqlite3.connect(self.name)
        cursor = conn.cursor()
        try:
            cursor.executemany(
                "INSERT INTO cryptoData(DATA,TXID,COIN,DATA_TYPE,BLOCK_HEIGHT,EXTRA_INDEX) values(?,?,?,?,?,?)",
                records
            )
        except sqlite3.IntegrityError:
            return
        except BaseException:
            raise

        cursor.close()
        conn.commit()
        conn.close()

    def insert_record(
        self,
        data: str,
        txid: str,
        coin: COIN,
        data_type: DATATYPE,
        block_height: int,
        extra_index: int,
    ) -> None:
        conn = sqlite3.connect(self.name)
        """Insert a new record into the database."""
        try:
            conn.execute(
                "INSERT INTO cryptoData(DATA,TXID,COIN,DATA_TYPE,BLOCK_HEIGHT,EXTRA_INDEX) values(?,?,?,?,?,?)",
                (data, txid, coin.value, data_type.value, block_height, extra_index),
            )
            conn.commit()
            conn.close()
        except sqlite3.IntegrityError:
            return
        except BaseException:
            raise

    def get_records(self, txid: str, extra_index: int) -> None:
        conn = sqlite3.connect(self.name)
        """Print all the records in the database."""
        c = self.conn.cursor()
        c.execute(
            "SELECT * FROM  cryptoData WHERE txid=? AND extra_index=?",
            (txid, extra_index),
        )
        result = c.fetchall()
        conn.commit()
        conn.close()
        print(result)

    def get_data(self, data_type: DATATYPE) -> List[bytes]:
        conn = sqlite3.connect(self.name)
        c = conn.cursor()
        c.execute("SELECT data FROM cryptoData WHERE data_type=?",
                  (data_type.value,))
        results = c.fetchall()
        return results
