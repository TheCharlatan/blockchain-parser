import enum
import sqlite3
from typing import Any, Callable, Iterable, NamedTuple, List, Optional

from eth_typing import BlockNumber


class BLOCKCHAIN(enum.Enum):
    """Coin/Blockchain"""

    BITCOIN_MAINNET = "bitcoin_mainnet"
    BITCOIN_TESTNET3 = "bitcoin_testnet3"
    BITCOIN_REGTEST = "bitcoin_regtest"
    MONERO_MAINNET = "monero_mainnet"
    MONERO_STAGENET = "monero_stagnet"
    MONERO_TESTNET = "monero_testnet"
    ETHEREUM_MAINNET = "ethereum_mainnet"


def coinStringToCoin(name: str) -> BLOCKCHAIN:
    if name == "bitcoin_mainnet":
        return BLOCKCHAIN.BITCOIN_MAINNET
    elif name == "bitcoin_testnet3":
        return BLOCKCHAIN.BITCOIN_TESTNET3
    elif name == "bitcoin_regtest":
        return BLOCKCHAIN.BITCOIN_REGTEST
    elif name == "monero_mainnet":
        return BLOCKCHAIN.MONERO_MAINNET
    elif name == "monero_stagenet":
        return BLOCKCHAIN.MONERO_STAGENET
    elif name == "monero_testnet":
        return BLOCKCHAIN.MONERO_TESTNET
    elif name == "ethereum_mainnet":
        return BLOCKCHAIN.ETHEREUM_MAINNET
    else:
        raise BaseException("invalid coin name")


class DATATYPE(enum.Enum):
    """Transaction Data Fields"""

    SCRIPT_SIG = "scriptsig"  # input transaction data
    SCRIPT_PUBKEY = "script_pubkey"  # output transaction data
    TX_EXTRA = "tx_extra"
    TX_DATA = "tx_data"


class DetectorPayload(NamedTuple):
    txid: str
    data_type: str
    extra_index: int
    data: bytes


class DetectedAsciiPayload(NamedTuple):
    txid: str
    data_type: str
    extra_index: int
    detected_data_length: int


class DetectedFilePayload(NamedTuple):
    txid: str
    data_type: str
    extra_index: int
    detected_data_type: str


class CryptoDataRecord(NamedTuple):
    data: bytes
    txid: str
    coin: str
    data_type: str
    block_height: int
    extra_index: int


class ASCIIHistogram(NamedTuple):
    string_length: int
    string_length_count: int


DetectorFunc = Callable[[DetectorPayload], Optional[NamedTuple]]


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
                EXTRA_INDEX INTEGER NOT NULL,
                PRIMARY KEY (TXID, EXTRA_INDEX, DATA_TYPE),
                UNIQUE(TXID, EXTRA_INDEX, DATA_TYPE)
            );"""
            )
            print("Crypto Data Table successfully created")
  
        c.execute(
            """ SELECT count(name) FROM sqlite_master WHERE type='table' AND name='asciiData' """
        )
        if not c.fetchone()[0] == 1:
            c.execute(
                """CREATE TABLE asciiData(
                    TXID CHAR(64) NOT NULL,
                    DATA_TYPE TEXT NOT NULL,
                    EXTRA_INDEX INTEGER,
                    STRING_LENGTH INTEGER NOT NULL,
                    FOREIGN KEY(TXID, EXTRA_INDEX, DATA_TYPE) REFERENCES cryptoData(TXID, EXTRA_INDEX, DATA_TYPE)
                );"""
            )
            print("asciiData Table successfully created")

        c.execute(
            """ SELECT count(name) FROM sqlite_master WHERE type='table' AND name='magicFileData' """
        )
        if not c.fetchone()[0] == 1:
            c.execute(
                """CREATE TABLE magicFileData(
                    TXID CHAR(64) NOT NULL,
                    DATA_TYPE TEXT NOT NULL,
                    EXTRA_INDEX INTEGER,
                    FILE_TYPE TEXT NOT NULL,
                    FOREIGN KEY(TXID, EXTRA_INDEX, DATA_TYPE) REFERENCES cryptoData(TXID, EXTRA_INDEX, DATA_TYPE)
                );"""
            )
            print("magicFileData Table successfully created")

        c.execute(
            """ SELECT count(name) FROM sqlite_master WHERE type='table' AND name='imghdrFileData' """
        )
        if not c.fetchone()[0] == 1:
            c.execute(
                """CREATE TABLE imghdrFileData(
                    TXID CHAR(64) NOT NULL,
                    DATA_TYPE TEXT NOT NULL,
                    EXTRA_INDEX INTEGER,
                    FILE_TYPE TEXT NOT NULL,
                    FOREIGN KEY(TXID, EXTRA_INDEX, DATA_TYPE) REFERENCES cryptoData(TXID, EXTRA_INDEX, DATA_TYPE)
                );"""
            )
            print("imghdrFileData Table successfully created")


        conn.commit()
        conn.close()

    def insert_records(
        self,
        records: Iterable[Iterable],
    ) -> None:
        conn = sqlite3.connect(self.name)
        try:
            conn.executemany(
                "INSERT INTO cryptoData(DATA,TXID,COIN,DATA_TYPE,BLOCK_HEIGHT,EXTRA_INDEX) values(?,?,?,?,?,?)",
                records
            )
        except sqlite3.IntegrityError:
            return
        except BaseException:
            raise

        conn.commit()
        conn.close()

    def insert_record(
        self,
        data: str,
        txid: str,
        coin: BLOCKCHAIN,
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
        c = conn.cursor()
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

    def ascii_histogram(self, blockchain: Optional[BLOCKCHAIN]) -> List[ASCIIHistogram]:
        conn = sqlite3.connect(self.name)
        c = conn.cursor()
        c.execute("SELECT STRING_LENGTH, COUNT(STRING_LENGTH) FROM asciiData GROUP BY STRING_LENGTH ORDER BY STRING_LENGTH")
        results = c.fetchall()
        return results

    def insert_detected_ascii_records(
        self,
        records: Iterable[DetectedAsciiPayload],
        conn: sqlite3.Connection
    ) -> None:
        c = conn.cursor()
        try:
            c.executemany(
                "INSERT INTO asciiData(TXID,DATA_TYPE,EXTRA_INDEX,STRING_LENGTH) values (?,?,?,?)",
                records
            )

        except sqlite3.IntegrityError:
            print("integrity error")
            return
        except BaseException:
            print("base exception")
            raise
        c.close()

    def insert_detected_magic_file_records(
        self,
        records: Iterable[DetectedAsciiPayload],
        conn: sqlite3.Connection
    ) -> None:
        c = conn.cursor()
        try:
            c.executemany(
                "INSERT INTO magicFileData(TXID,DATA_TYPE,EXTRA_INDEX,FILE_TYPE) values (?,?,?,?)",
                records
            )
        except sqlite3.InterfaceError:
            print("integrity error")
            return
        except BaseException:
            print("base exception")
            raise
        c.close()

    def insert_detected_imghdr_file_records(
        self,
        records: Iterable[DetectedAsciiPayload],
        conn: sqlite3.Connection
    ) -> None:
        c = conn.cursor()
        try:
            c.executemany(
                "INSERT INTO imghdrFileData(TXID,DATA_TYPE,EXTRA_INDEX,FILE_TYPE) values (?,?,?,?)",
                records
            )
        except sqlite3.InterfaceError:
            print("integrity error")
            return
        except BaseException:
            print("base exception")
            raise
        c.close()


    def run_detection(self, detector: DetectorFunc, database_write_func: Callable[[Iterable[NamedTuple], sqlite3.Connection], None], blockchain: Optional[BLOCKCHAIN]) -> None:
        conn = sqlite3.connect(self.name)
        counter = 0
        detected_count = 0
        res = conn.execute("SELECT COUNT(TXID) FROM cryptoData")
        for i in res:
            res = i
        prepared_query = "SELECT * FROM cryptoData"
        if blockchain is not None:
            prepared_query += "WHERE COIN=blockchain.value"
        results = []
        for (data, txid, _, data_type, _, extra_index) in conn.cursor().execute("SELECT * FROM cryptoData"):
            counter += 1
            detected = detector(DetectorPayload(txid, data_type, extra_index, data))
            if detected is None:
                continue
            # cache results for future batched write
            results.append(detected)
            detected_count += 1
            if len(results) > 100:
                database_write_func(results, conn)
                print("counter: ", counter, "number detected: ", detected_count, "total rows: ", res)
                conn.commit()
                results = []

        # write and commit left-over results
        database_write_func(results, conn)
        conn.commit()
        print("\n\n\nCompleted detection!\n\n\n")
        print("counter: ", counter, "number detected: ", detected_count, "total rows: ", res)
