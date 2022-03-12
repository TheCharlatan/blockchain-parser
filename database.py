import enum
import sqlite3
from typing import Callable, Iterable, NamedTuple, List


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


class LABEL(enum.Enum):
    """Default Data labels"""

    OP_RETURN = "opreturn"
    TEXT = "text"
    IMAGE = "image"

class DetectorPayload(NamedTuple):
    txid: str
    data_type: str
    extra_index: int
    data: bytes


class DetectedDataPayload(NamedTuple):
    txid: str
    data_type: str
    extra_index: int
    data_length: int


class CryptoDataRecord(NamedTuple):
    data: bytes
    txid: str
    coin: str
    data_type: str
    block_height: int
    extra_index: int


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

    def insert_detected_ascii_records(
        self,
        records : Iterable[DetectedDataPayload],
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
        # print("ascii data written")


    # def run_detection(self, detector_event_sender: zmq.Socket, database_event_receiver: zmq.Socket) -> None:
        # conn = sqlite3.connect(self.name)
        # detected_counter = 0
        # iterated_counter = 0
        # buffer: List[DetectedDataPayload] = []
        # for (data, txid, _, data_type, _, extra_index) in conn.cursor().execute("SELECT * FROM cryptoData"):
            # iterated_counter += 1
            # detector_event_sender.send_pyobj(DetectorPayload(txid, data_type, extra_index, data))
            # 
            # if iterated_counter % 1000 == 0:
                # print(iterated_counter)
            # 
            # try:
                # buffer.append(database_event_receiver.recv_pyobj(zmq.NOBLOCK))
                # detected_counter += 1
            # except zmq.ZMQError:
                # continue
            # 
            # if len(buffer) > 100:
                # print(detected_counter)
                # self.insert_detected_ascii_records(buffer, conn)
                # buffer= []
        # 
        # conn.commit()
        # conn.close()
        # 
        # print("\n\n\nCompleted detection!\n\n\n")
        # 

    def run_detection(self, detector: Callable[[DetectorPayload], DetectedDataPayload]) -> None:
        conn = sqlite3.connect(self.name)
        counter = 0
        detected_count = 0
        res = conn.execute("SELECT COUNT(TXID) FROM cryptoData")
        for i in res:
            res = i
        results = []
        for (data, txid, _, data_type, _, extra_index) in conn.cursor().execute("SELECT * FROM cryptoData"):
            counter += 1
            detected = detector(DetectorPayload(txid, data_type, extra_index, data))
            if detected is None:
                continue
            if detected.data_length > 8:
                detected_count += 1
                results.append(detected)
                if len(results) > 100:
                    print("writing data")
                    # self.insert_detected_ascii_records(results, conn)
                    print("counter: ", counter, "number detected: ", detected_count, "total rows: ", res)
                    results = []
            conn.commit()
        print("\n\n\nCompleted detection!\n\n\n")
        print("counter: ", counter, "number detected: ", detected_count, "total rows: ", res)

