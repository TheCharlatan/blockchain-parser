from typing import Optional
from database import COIN, DATATYPE, Database
import lmdb
from monero_serialize import xmrserialize as x
from monero_serialize import xmrtypes as xmr
from monero_serialize import core as monero_core
import asyncio
import struct
import binascii
import detectors
from parser import CoinParser


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
    monero_tx = await archiver.message(None, xmr.TransactionPrefix)
    return monero_tx


async def serialize_uint64(number: int) -> bytearray:
    """Serialize a number to a uint64 in byte representation
    :param number: Number to be serialized.
    :type number: int
    :return: The serialized number in bytes
    :rtype: bytearray
    """

    writer = x.MemoryReaderWriter()
    await monero_core.int_serialize.dump_uint(writer, number, 8)
    db_tx_index = bytearray(writer.get_buffer())
    return db_tx_index


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


class MoneroParser(CoinParser):
    def __init__(self, blockchain_path: str, coin: COIN) -> None:
        """
        :param blockchain_path: Path to the Monero lmdb directory (e.g. /home/user/.bitmonero/stagenet/lmdb).
        :type blockchain_path: str
        :param coin: One of the Monero compatible coins.
        :type coin: COIN
        """

        self.blockchain_path = blockchain_path
        self.coin = coin

    def parse_blockchain(self, database: Optional[Database]):
        """Parse the blockchain with the previously constructed options
        :param database: Database to be written into.
        :type database: Database
        """

        print(lmdb.version())
        env = lmdb.open(
            "/home/drgrid/.bitmonero/stagenet/lmdb",
            subdir=True,
            lock=False,
            readonly=True,
            max_dbs=10,
        )

        index_db = env.open_db(
            b"tx_indices", integerkey=True, dupsort=True, dupfixed=True
        )
        tx_db = env.open_db(b"txs_pruned", integerkey=True, dupsort=True, dupfixed=True)

        with env.begin(write=False) as txn:
            for _, value in txn.cursor(db=index_db):
                # Get the TxIndex struct from the database value
                monero_tx_index = asyncio.get_event_loop().run_until_complete(
                    deserialize_tx_index(value)
                )

                # Convert the extracted database transaction id from uint64 back to bytes
                db_tx_index = asyncio.get_event_loop().run_until_complete(
                    serialize_uint64(monero_tx_index.data.tx_id)
                )

                # Get the full transaction from the database with the transaction id bytes
                monero_tx_raw = txn.get(db_tx_index, db=tx_db)
                monero_tx = asyncio.get_event_loop().run_until_complete(
                    deserialize_transaction(monero_tx_raw)
                )

                # Extract the extra bytes from the monero serialized data,
                extra_bytes = struct.pack(
                    "{}B".format(len(monero_tx.extra)), *monero_tx.extra
                )

                # Ignore extra bytes that are in the default format - they are unlikely to contain data
                if is_default_extra(extra_bytes):
                    continue

                if database is not None:
                    database.insert_record(
                        extra_bytes,
                        value.key,
                        self.coin,
                        DATATYPE.TX_EXTRA,
                        monero_tx_index.data.block_id,
                        0,
                    )
                else:
                    # Scan for strings in the extracted data to reduce data retained on disk
                    detected_text = detectors.gnu_strings(extra_bytes, 10)
                    if detected_text:
                        print(detected_text, binascii.hexlify(monero_tx_index.key))

            print("\n\nCompleted Monero Database parsing\n\n")
