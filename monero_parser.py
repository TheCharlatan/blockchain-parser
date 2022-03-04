from calendar import c
from typing import List, Optional
from database import COIN, DATATYPE, Database
import lmdb
from monero_serialize import xmrserialize as x
from monero_serialize import xmrtypes as xmr
import asyncio
import struct
from parser import CoinParser
import threading
import zmq
import pickle

def async_results(i):
    return i[1]

class TxParser(threading.Thread):
    """TxParser acts as a worker thread for parsing raw monero transactions
    and communicates through zmq sockets"""

    def __init__(self, receiver: zmq.Socket, sender: zmq.Socket):
        """
        :param receiver: Receives raw transactions to parse.
        :type receiver: zmq.Socket
        :param sender: Sends parsed transactions.
        :type sender: zmq.Socket
        """
        self._receiver = receiver
        self._sender = sender
        threading.Thread.__init__(self)
    
    def run(self) -> None:
        loop = asyncio.new_event_loop()
        while True:
            print("parsing monero transactions...")
            [counter, monero_txs_raw, monero_tx_indices] = pickle.loads(self._receiver.recv())
            monero_txs = loop.run_until_complete(
                deserialize_transactions(map(async_results, monero_txs_raw))
            )

            # Extract the extra bytes from the monero serialized data,
            extra_bytes_list = [struct.pack(
                "{}B".format(len(monero_tx.extra)), *monero_tx.extra
            ) for monero_tx in monero_txs]

            print("parsed monero transactions")
                
            self._sender.send(pickle.dumps([counter, extra_bytes_list, monero_tx_indices]))


class DatabaseWriter(threading.Thread):
    """DatabaseWriter acts as a worker thread for writing to the sql database
    and receives from a zmq socket"""

    def __init__(self, database: Database, receiver: zmq.Socket, coin: COIN):
        """
        :param database: Database to be written into
        :type database: Database
        :param receiver: Receives parsed extra bytes and monero transaction indices
        :type receiver: zmq.Socket
        :param coin: Some monero coin
        :type coin: Coin"""
        self._db = database
        self._receiver = receiver
        self._coin = coin
        threading.Thread.__init__(self)
    
    def run(self):
        default_extra_counter = 0

        while True:
            [counter, extra_bytes_list, monero_tx_indices] = pickle.loads(self._receiver.recv())
            print("writing " + self._coin)
            records = []

            for i in range(len(extra_bytes_list)):
                if is_default_extra(extra_bytes_list[i]):
                    default_extra_counter += 1
                    continue

                record = (
                    extra_bytes_list[i],
                    bytes(monero_tx_indices[i].key).hex(),
                    self._coin.value,
                    DATATYPE.TX_EXTRA.value,
                    monero_tx_indices[i].data.block_id,
                    0,
                )
                records.append(record)
            
            self._db.insert_records(records)

            print("written ", self._coin, counter, default_extra_counter)


async def deserialize_tx_index(tx_index_raw: bytes) -> xmr.TxIndex:
    """Deserialize raw bytes retrieved from the tx_indices LMDB table
    :param tx_index_raw: Raw tx_indeces bytes.
    :type tx_index_raw: bytes
    :return: The de-serialized TxIndex
    :rtype: monero_serialize.xmrtypes.TxIndex
    """

    reader = x.MemoryReaderWriter(bytearray(tx_index_raw))
    archiver = x.Archive(reader, False, xmr.hf_versions(9))
    monero_tx_indices = await archiver.message(None, xmr.TxIndex)
    return monero_tx_indices


async def deserialize_transaction(monero_tx_raw: bytes) -> xmr.TransactionPrefix:
    """Deserialize raw bytes retrieved from the txs_pruned LMDB table
    :param monero_tx_raw: Raw txs_pruned bytes.
    :type monero_tx_raw: bytes
    :return: The de-serialized TransactionPrefix
    :rtype: monero_serialize.xmrtypes.TransactionPrefix
    """

    reader = x.MemoryReaderWriter(bytearray(monero_tx_raw))
    archiver = x.Archive(reader, False, xmr.hf_versions(9))
    try:
        monero_tx = await archiver.message(None, xmr.TransactionPrefix)
    except ValueError:
        reader = x.MemoryReaderWriter(bytearray(monero_tx_raw))
        archiver = x.Archive(reader, False, xmr.hf_versions(9))
        monero_tx = await archiver.message(None, xmr.TransactionPrefix)
    except:
        print(monero_tx_raw)
        raise
    return monero_tx


def is_default_extra(extra: bytes) -> bool:
    """Checks if the tx_extra follows the standard format of:
            0x01 <pubkey> 0x02 0x09 0x01 <encrypted_payment_id>
    :param extra: Potential default extra bytes.
    :type extra: bytes
    :return: True if the passed in bytes are in the default tx_extra format
    :rtype: bool
    """

    if len(extra) != 1 + 32 + 1 + 1 + 1 + 8:
        return False
    if (
        extra[0] == 0x01
        and extra[33] == 0x02
        and extra[34] == 0x09
        and extra[35] == 0x01
    ):
        return True
    return False

async def stop_all():
    """Dummy function for asyncio.gather"""
    return ""

async def deserialize_tx_indices(values: List[bytes]):
    """
    :param values: List of raw tx indices
    :type values: List[bytes]
    """
    tasks = (deserialize_tx_index(value) for value in values)
    done = await asyncio.gather(stop_all(), *tasks)
    # the first entry is empty for some reason
    return done[1:]

async def deserialize_transactions(monero_txs_raw: List[bytes]):
    """
    :param monero_txs_raw: List of raw monero transactions
    :type monero_txs_raw: List[bytes]
    """
    tasks = (deserialize_transaction(monero_tx_raw) for monero_tx_raw in monero_txs_raw)
    done = await asyncio.gather(stop_all(), *tasks)
    # the first entry is empty for some reason
    return done[1:]


class MoneroParser(CoinParser):
    def __init__(self, blockchain_path: str, coin: COIN) -> None:
        """
        :param blockchain_path: Path to the Monero lmdb directory (e.g. /home/user/.bitmonero).
        :type blockchain_path: str
        :param coin: One of the Monero compatible coins.
        :type coin: COIN
        """

        self.blockchain_path = blockchain_path + "/lmdb"
        self.coin = coin

    def parse_blockchain(self, database: Optional[Database]):
        """Parse the blockchain with the previously constructed options
        :param database: Database to be written into.
        :type database: Database
        """

        print(lmdb.version())
        env = lmdb.open(
            self.blockchain_path,
            subdir=True,
            lock=False,
            readonly=True,
            max_dbs=10,
        )

        index_db = env.open_db(
            b"tx_indices", integerkey=True, dupsort=True, dupfixed=True
        )
        tx_db = env.open_db(b"txs_pruned", integerkey=True)

        context = zmq.Context()

        tx_parser_event_sender = context.socket(zmq.PAIR)
        tx_parser_event_receiver = context.socket(zmq.PAIR)
        tx_parser_event_sender.bind("inproc://monero_txbridge")
        tx_parser_event_receiver.connect("inproc://monero_txbridge")

        database_event_sender = context.socket(zmq.PAIR)
        database_event_receiver = context.socket(zmq.PAIR)
        database_event_sender.bind("inproc://monero_dbbridge")
        database_event_receiver.connect("inproc://monero_dbbridge")

        tx_reader = TxParser(tx_parser_event_receiver, database_event_sender)
        tx_reader.start()
        writer = DatabaseWriter(database, database_event_receiver, self.coin)
        writer.start()

        values = []
        counter = 0
        with env.begin(write=False) as txn:
            for _, value in txn.cursor(db=index_db):
                counter += 1
                values.append(value)
                if len(values) == 10000:

                    # Get the TxIndex struct from the database value
                    monero_tx_indices = asyncio.get_event_loop().run_until_complete(
                        deserialize_tx_indices(values)
                    )

                    # translate the tx index back to bytes for retrieval of the full transaction
                    db_tx_indices = [monero_tx_index.data.tx_id.to_bytes(8, "little") for monero_tx_index in monero_tx_indices]

                    print("getting monero transaction")
                    # Get the full transaction from the database with the transaction id bytes
                    cursor = txn.cursor(db=tx_db)
                    monero_txs_raw = cursor.getmulti(db_tx_indices)
                    cursor.close()
                    print("got monero transaction")
                    tx_parser_event_sender.send(pickle.dumps([counter, monero_txs_raw, monero_tx_indices]))

                    values = []
                    print(counter)

            print("\n\nCompleted Monero Database parsing\n\n")
