import lmdb
from monero_serialize import xmrserialize as x
from monero_serialize import xmrtypes as xmr
from monero_serialize import core as monero_core
import asyncio
import struct
import subprocess
import binascii


def find_string(bytestring: bytes, min: int = 10) -> str:
    """Find and return a string with the specified minimum size."""
    cmd = "strings -n {}".format(min)
    process = subprocess.Popen(
        cmd,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        stdin=subprocess.PIPE,
    )
    process.stdin.write(bytestring)
    output = process.communicate()[0]
    return output.decode("ascii").strip()


async def extract() -> None:
    print(lmdb.version())
    # env = lmdb.Environment("/home/drgrid/.bitmonero/fake/lmdb")
    env = lmdb.open(
        "/home/drgrid/.bitmonero/stagenet/lmdb",
        subdir=True,
        lock=False,
        readonly=True,
        max_dbs=10,
    )
    block_heights_db = env.open_db(
        b"block_heights", integerkey=True, dupsort=True, dupfixed=True
    )
    # with env.begin(db=block_heights_db) as txn:
    #     print(env)
    #     res = txn.get(key=b'\x00\x00\x00\x00\x00\x00\x00\x00')
    #     print(res)
    #     res = txn.get(key=b'\x00\x00\x00\x00\x00\x00\x00\x00')
    #     print(res.hex())
    #     cursor = txn.cursor()
    #     for key, value in cursor:
    #         print(key, value)

    index_db = env.open_db(b"tx_indices", integerkey=True, dupsort=True, dupfixed=True)
    txids = {}

    with env.begin(db=index_db) as txn:
        cursor = txn.cursor()
        i = 0
        unlock_time_count = 0

        for key, value in cursor:
            i += 1
            reader = x.MemoryReaderWriter(bytearray(value))
            ar1 = x.Archive(reader, False, xmr.hf_versions(9))
            res = await ar1.message(None, xmr.TxIndices)
            print(binascii.hexlify(res.key))

            # if i == 1000:
            #     print(unlock_time_count)
            #     print(len(txids))
            #     break

            if res.data.unlock_time > 0:
                unlock_time_count += 1

            txids[res.data.tx_id] = res.key

        print("processed rows: ", i)
        print("unlock time set for: ", unlock_time_count)
        print("number of txs: ", len(txids))
        print("0th entry: ", txids[0])
        print("1st entry: ", txids[1])
        print("2nd entry: ", txids[2])

    tx_db = env.open_db(b"txs_pruned", integerkey=True, dupsort=True, dupfixed=True)
    with env.begin(db=tx_db) as txn:
        cursor = txn.cursor()
        for key, value in cursor:
            reader = x.MemoryReaderWriter(bytearray(value))
            ar = x.Archive(reader, False, xmr.hf_versions(9))
            res = await ar.message(None, xmr.TransactionPrefix)

            reader = x.MemoryReaderWriter(bytearray(key))
            ar = x.Archive(reader, False, xmr.hf_versions(9))
            tx_index = await monero_core.int_serialize.load_uint(reader, 8)

            extra_bytes = struct.pack("{}B".format(len(res.extra)), *res.extra)
            detected_text = find_string(extra_bytes, 15)
            if detected_text:
                print(detected_text, binascii.hexlify(txids[tx_index]))

        for tx_id in txids:
            writer = x.MemoryReaderWriter()
            ar = x.Archive(writer, True, xmr.hf_versions(9))
            await ar.root()
            await monero_core.int_serialize.dump_uint(writer, tx_id, 8)
            tx = txn.get(bytearray(writer.get_buffer()))

            reader = x.MemoryReaderWriter(bytearray(tx))
            ar1 = x.Archive(reader, False, xmr.hf_versions(9))
            res = await ar1.message(None, xmr.TransactionPrefix)

            extra_bytes = struct.pack("{}B".format(len(res.extra)), *res.extra)
            detected_text = find_string(extra_bytes, 15)
            if detected_text:
                print(detected_text, binascii.hexlify(txids[tx_id]))

        txn.get()
        cursor = txn.cursor()
        i = 0
        for key, value in cursor:
            print(key)
            i += 1
            if len(value) > 0:
                reader = x.MemoryReaderWriter(bytearray(value))
                ar1 = x.Archive(reader, False, xmr.hf_versions(9))
                res = await ar1.message(None, xmr.TransactionPrefix)
                # print(res)
                extra_bytes = struct.pack("{}B".format(len(res.extra)), *res.extra)
                detected_text = find_string(extra_bytes, 35)
                if detected_text:
                    print(detected_text)

    block_heights_db = env.open_db(
        b"blocks", integerkey=True, dupsort=True, dupfixed=True
    )
    with env.begin(db=block_heights_db) as txn:
        cursor = txn.cursor()
        i = 0
        for key, value in cursor:
            # print("id: ", key, " value: ", value)
            reader = x.MemoryReaderWriter(bytearray(value))
            ar1 = x.Archive(reader, False, xmr.hf_versions(9))
            res = await ar1.message(None, xmr.Block)
            # print("res: ", res)
            length = len(res.miner_tx.extra)
            extra_bytes = struct.pack(
                "{}B".format(len(res.miner_tx.extra)), *res.miner_tx.extra
            )
            # print(bytes, len(bytes))
            detected_text = find_string(extra_bytes, 10)
            if detected_text:
                print(detected_text)

            # if (length != 33 and length != 43):
            #     print("miner extra:", res.miner_tx.extra,
            #           len(res.miner_tx.extra))
            #     print(type(res.miner_tx.extra))

            # if (len(res.tx_hashes) != 0):
            #     print("tx hashes: ", res.tx_hashes)
            i += 1
            if i % 1000 == 0:
                print("iterating block:", i)


loop = asyncio.get_event_loop()
result = loop.run_until_complete(extract())
