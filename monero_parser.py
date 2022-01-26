from typing import Callable, Optional
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
    reader = x.MemoryReaderWriter(bytearray(tx_index_raw))
    archiver = x.Archive(reader, False, xmr.hf_versions(9))
    monero_tx_indices = await archiver.message(None, xmr.TxIndex)
    return monero_tx_indices


async def deserialize_transaction(monero_tx_raw: bytes) -> xmr.TransactionPrefix:
    reader = x.MemoryReaderWriter(bytearray(monero_tx_raw))
    archiver = x.Archive(reader, False, xmr.hf_versions(9))
    monero_tx = await archiver.message(None, xmr.TransactionPrefix)
    return monero_tx


async def serialize_uint64(number: int) -> bytearray:
    writer = x.MemoryReaderWriter()
    await monero_core.int_serialize.dump_uint(writer, number, 8)
    db_tx_index = bytearray(writer.get_buffer())
    return db_tx_index


class MoneroParser(CoinParser):

    def __init__(self, blockchain_path: str) -> None:
        self.blockchain_path = blockchain_path

    def parse_blockchain(filter: Callable[[bytes, Optional[int]], str]):
        print(lmdb.version())
        env = lmdb.open("/home/drgrid/.bitmonero/stagenet/lmdb", subdir=True,
                        lock=False, readonly=True, max_dbs=10)

        index_db = env.open_db(
            b"tx_indices", integerkey=True, dupsort=True, dupfixed=True)
        tx_db = env.open_db(
            b"txs_pruned", integerkey=True, dupsort=True, dupfixed=True)

        with env.begin(write=False) as txn:
            for _, value in txn.cursor(db=index_db):
                # Get the TxIndex struct from the database value
                monero_tx_index = asyncio.get_event_loop().run_until_complete(
                    deserialize_tx_index(value))

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
                extra_bytes = struct.pack("{}B".format(
                    len(monero_tx.extra)), *monero_tx.extra)

                # Scan for strings in the extracted data to reduce data retained on disk
                detected_text = filter(extra_bytes, 10)
                if detected_text:
                    print(detected_text, binascii.hexlify(
                        monero_tx_index.key))

            print("\n\nCompleted Monero Database parsing\n\n")
            return "Complete"


async def extract() -> str:
    print(lmdb.version())
    env = lmdb.open("/home/drgrid/.bitmonero/stagenet/lmdb", subdir=True,
                    lock=False, readonly=True, max_dbs=10)

    index_db = env.open_db(
        b"tx_indices", integerkey=True, dupsort=True, dupfixed=True)
    tx_db = env.open_db(
        b"txs_pruned", integerkey=True, dupsort=True, dupfixed=True)

    with env.begin(write=False) as txn:
        for _, value in txn.cursor(db=index_db):
            # Get the TxIndex struct from the database value
            reader = x.MemoryReaderWriter(bytearray(value))
            archiver = x.Archive(reader, False, xmr.hf_versions(9))
            monero_tx_indices = await archiver.message(None, xmr.TxIndex)

            # Convert the extracted database transaction id back to bytes
            writer = x.MemoryReaderWriter()
            await monero_core.int_serialize.dump_uint(writer, monero_tx_indices.data.tx_id, 8)
            tx_index = bytearray(writer.get_buffer())

            # Get the full transaction from the database with the transaction id bytes
            monero_tx_raw = txn.get(tx_index, db=tx_db)
            reader = x.MemoryReaderWriter(bytearray(monero_tx_raw))
            archiver = x.Archive(reader, False, xmr.hf_versions(9))
            monero_tx = await archiver.message(None, xmr.TransactionPrefix)

            # Extract the extra bytes from the monero serialized data,
            extra_bytes = struct.pack("{}B".format(
                len(monero_tx.extra)), *monero_tx.extra)

            # Scan for strings in the extracted data
            detected_text = detectors.native_strings(extra_bytes, 10)
            if detected_text:
                print(detected_text, binascii.hexlify(monero_tx_indices.key))

    print("\n\nCompleted Monero Database parsing\n\n")
    return "Complete"

loop = asyncio.get_event_loop()
result = loop.run_until_complete(extract())
print(result)
