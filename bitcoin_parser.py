from re import U
import threading
from typing import Iterable, List, NamedTuple
from blockchain_parser.blockchain import Blockchain
import zmq
from database import BLOCKCHAIN, DATATYPE, CryptoDataRecord, Database
from parser import DataExtractor
import bitcoin.rpc
import os
from bitcoin_utxo_iterator import UTXOIterator
from pathlib import Path
from bitcoin.core import CScript, script, CTransaction

class BitcoinDataMessage(NamedTuple):
    """ZMQ Message for the DatabaseWriter thread with contents to be written to the database"""

    data: bytes
    txid: str
    data_type: DATATYPE
    block_height: int
    extra_index: int


class DatabaseWriter(threading.Thread):
    """DatabaseWriter acts as a worker thread for writing to the sql database
    and receives from a zmq socket"""

    def __init__(
        self, database: Database, receiver: zmq.Socket, blockchain: BLOCKCHAIN
    ):
        """
        :param database: Database to be written into
        :type database: Database
        :param receiver: Receives parsed extra bytes and monero transaction indices
        :type receiver: zmq.Socket
        :param blockchain: Some Bitcoin-compatible blockchain
        :type blockchain: BLOCKCHAIN"""
        self._db = database
        self._receiver = receiver
        self._blockchain = blockchain
        threading.Thread.__init__(self)

    def run(self) -> None:
        records: List[CryptoDataRecord] = []
        while True:
            message: BitcoinDataMessage = self._receiver.recv_pyobj()

            records.append(
                CryptoDataRecord(
                    message.data,
                    message.txid,
                    self._blockchain.value,
                    message.data_type.value,
                    message.block_height,
                    message.extra_index,
                )
            )

            if len(records) > 500:
                print("writing:", records[0])
                self._db.insert_records(records)
                # print(self._coin.value + " written")
                records = []


opcode_counters = {
    script.OP_1: 1,
    script.OP_2: 2,
    script.OP_3: 3,
    script.OP_4: 4,
    script.OP_5: 5,
    script.OP_6: 6,
    script.OP_7: 7,
    script.OP_8: 8,
    script.OP_9: 9,
    script.OP_10: 10,
    script.OP_11: 11,
    script.OP_12: 12,
    script.OP_13: 13,
    script.OP_14: 14,
    script.OP_15: 15,
    script.OP_16: 16,
}


def is_DER_sig(sig: bytes) -> bool:
    """Checks if the data is a DER encoded ECDSA signature
        https://bitcoin.stackexchange.com/questions/92680/what-are-the-der-signature-and-sec-format
    :param sig: Potential signature.
    :type sig: bytes
    :return: True if the passed in bytes are an ECDSA signature in DER format.
    :rtype: bool
    """

    # Header byte
    if sig[0] != 0x30:
        return False
    # Header byte for the r big integer
    if sig[2] != 0x02:
        return False
    len_r = sig[3]
    # Header byte for the s big integer
    if sig[3 + len_r + 1] != 0x02:
        return False
    len_s = sig[3 + len_r + 2]

    # The last extra byte is the sighash flag
    computed_len = 4 + len_r + 2 + len_s + 1
    if len(sig) != computed_len:
        False
    return True


def is_pubkey(pubkey: bytes) -> bool:
    """Checks if the data is a SEC serialized ECDSA public key
            https://bitcoin.stackexchange.com/questions/92680/what-are-the-der-signature-and-sec-format
    :param pubkey: Potential public key.
    :type pubkey: bytes
    :return: True if the passed in bytes are an ECDSA public key in SEC format.
    :rtype: bool
    """

    if pubkey[0] == 0x02 or pubkey[0] == 0x03:
        return len(pubkey) == 33
    if pubkey[0] == 0x04:
        return len(pubkey) == 65
    return False


def is_pubkeys(pubkeys: bytes, number_of_keys: int) -> bool:
    """Checks if the data are multiple SEC serialized ECDSA public keys
            https://bitcoin.stackexchange.com/questions/92680/what-are-the-der-signature-and-sec-format
    :param pubkeys: Potential public keys.
    :type pubkey: bytes
    :return: True if the passed in bytes are multiple serialized ECDSA public keys in SEC format.
    :rtype: bool
    """

    if len(pubkeys) < 33:
        return False
    pos = 0
    for i in range(number_of_keys):
        if len(pubkeys) <= pos:
            return False
        if pubkeys[pos] == 0x02 or pubkeys[pos] == 0x03:
            pos += 34
        elif pubkeys[pos] == 0x04:
            pos += 66
        else:
            return False
    return True


def is_p2pk_scriptsig(script: CScript) -> bool:
    """Checks if the input script of the form:
            <sig>
    :param script: Script to be analyzed.
    :type script: CScript
    :return: True if the passed in bitcoin CScript is a p2pk input script.
    :rtype: bool
    """

    if len(script) < 64:
        return False
    is_p2pk = False
    # get rid of the pushdata:
    for (index, sig) in enumerate(script):
        if type(sig) is not bytes:
            return False
        if len(sig) < 64:
            return False

        if index > 0:
            return False
        if is_DER_sig(sig):
            is_p2pk = True
    return is_p2pk


def is_p2pkh_scriptsig(script: CScript) -> bool:
    """Checks if the input script of the form:
            <sig> <pubkey>
    :param script: Script to be analyzed.
    :type script: CScript
    :return: True if the passed in bitcoin CScript is a p2pkh input script.
    :rtype: bool
    """

    # checks if the input script is
    if len(script) < 96:
        return False
    for (elem_index, elem) in enumerate(script):
        if type(elem) is not bytes:
            return False
        if elem_index == 0:
            if is_DER_sig(elem):
                continue
            else:
                return False
        if elem_index == 1 and len(elem) > 32:
            if not is_pubkey(elem):
                return False
        else:
            return False
    return True


def is_p2sh_p2ms_scriptsig(cscript: CScript) -> bool:
    """Checks if the input script of the form:
            OP_0 <sigs> OP_N <pubkeys> OP_N OP_CHECKMULTISIG
    :param script: Script to be analyzed.
    :type script: CScript
    :return: True if the passed in bitcoin CScript is a p2sh(p2ms) input script.
    :rtype: bool
    """

    # P2SH inputs always start with OP_0
    if len(cscript) < 96:
        return False
    for (elem_index, elem) in enumerate(cscript):
        # This is pushed because of the P2MS bug: it always requires an extra element on the stack
        if elem == 0x00 and elem_index == 0:
            continue
        if type(elem) is not bytes:
            return False
        # Check the redeem script for p2ms
        if elem[0] in opcode_counters.keys():
            if elem[-1] != script.OP_CHECKMULTISIG:
                return False
            if elem[-2] not in opcode_counters.keys():
                return False
            number_of_pubkeys = opcode_counters[elem[-2]]
            number_of_sigs = opcode_counters[elem[0]]
            if is_pubkeys(elem[2:-2], number_of_pubkeys):
                continue
            return False
        # Check the signatures
        if not is_DER_sig(elem):
            return False

    return True


def is_p2sh_p2wpkh_scriptsig(script: CScript) -> bool:
    """Checks if the input script of the form:
            OP_O <hash>
    :param script: Script to be analyzed.
    :type script: CScript
    :return: True if the passed in bitcoin CScript is a p2sh(p2wpkh) input script.
    :rtype: bool
    """

    if len(script) != 23:
        return False
    if not script[1] == 0x00:
        return False
    return True


def is_p2pkh_output(cscript: CScript) -> bool:
    """Checks if the output script is of the form:
            OP_DUP OP_HASH160 <hash> OP_EQUALVERIFY OP_CHECKSIG
    :param script: Script to be analyzed.
    :type script: CScript
    :return: True if the passed in bitcoin CScript is a p2pkh output script.
    :rtype: bool
    """

    if len(cscript) != 25:
        return False
    return (
        cscript[0] == script.OP_DUP
        and cscript[1] == script.OP_HASH160
        and cscript[23] == script.OP_EQUALVERIFY
        and cscript[24] == script.OP_CHECKSIG
    )


def is_p2pk_output(cscript: CScript) -> bool:
    """Checks if the output script is of the form:
            <pubkey> OP_CHECKSIG
    :param script: Script to be analyzed.
    :type script: CScript
    :return: True if the passed in bitcoin CScript is a p2pk output script.
    :rtype: bool
    """

    if len(cscript) < 33:
        return False
    return is_pubkey(cscript[1:-1]) and cscript[-1] == script.OP_CHECKSIG


def is_p2sh_output(cscript: CScript) -> bool:
    """Checks if the output script is of the form:
            OP_HASH160 <hash> OP_EQUAL
    :param script: Script to be analyzed.
    :type script: CScript
    :return: True if the passed in bitcoin CScript is a p2sh output script.
    :rtype: bool
    """

    if len(cscript) != 23:
        return False
    return (
        cscript[0] == script.OP_HASH160
        and cscript[-1] == script.OP_EQUAL
    )


def is_p2ms_output(cscript: CScript) -> bool:
    """Checks if the output script is of the form:
            OP_N [OP_N] <pubkeys> [OP_N] OP_N OP_CHECKMULTISIG
    :param script: Script to be analyzed.
    :type script: bitcoin.core.script.CSCript
    :return: True if the passed in bitcoin CScript is a p2ms output script.
    :rtype: bool
    """

    if len(cscript) < 33:
        return False
    analyze_script = []
    for item in script:
        analyze_script.append(item)

    if analyze_script[-1] != OP_CHECKMULTISIG:
        return False

    if type(analyze_script[0]) == int and type(analyze_script[-2]) == int:
        first_key_index = 1
        last_key_index = len(analyze_script) - 3
        n = analyze_script[-2]
        if (type(analyze_script[1]) == int): # There might be another value here for the extended multisig encodign
            first_key_index = 2
        if (type(analyze_script[-3]) == int): # There also might be another value here for the extended multisig encoding
            n += analyze_script[-3]
            last_key_index = len(analyze_script) - 4
        
        if len(analyze_script[first_key_index:last_key_index+1]) != n:
            print("Wrong number of pubkeys: ", len(analyze_script[first_key_index:last_key_index+1]), "Expected: ", n)
            return False
        
        for pubkey in analyze_script[first_key_index:last_key_index+1]:
            if type(pubkey) != bytes:
                return False
        
        return True
    return False


def is_p2wpkh_output(cscript: CScript) -> bool:
    """Checks if the output script if of the form:
            OP_0 <pubkey hash>
    :param script: Script to be analyzed.
    :type script: CScript
    :return: True if the passed in bitcoin CScript is a p2wpkh output script.
    :rtype: bool
    """

    if len(cscript) != 22:
        return False
    return cscript[0] == script.OP_0


def is_p2wsh_output(cscript: CScript) -> bool:
    """Checks if the output script if of the form:
            OP_0 <script hash>
    :param script: Script to be analyzed.
    :type script: CScript
    :return: True if the passed in bitcoin CScript is a p2wsh output script.
    :rtype: bool
    """

    if len(cscript) != 34:
        return False
    return cscript[0] == script.OP_0


def is_p2tr_output(cscript: CScript) -> bool:
    """Checks if the output script if of the form:
            OP_1 <x only pubkey>
    :param script: Script to be analyzed.
    :type script: CScript
    :return: True if the passed in bitcoin CScript is a p2wtr output script.
    :rtype: bool
    """

    if len(cscript) != 34:
        return False
    return cscript[0] == script.OP_1


class BitcoinParser(DataExtractor):
    def __init__(self, blockchain_path: Path, blockchain: BLOCKCHAIN):
        """
        :param blockchain_path: Path to the Bitcoin blockchain (e.g. /home/user/.bitcoin/).
        :type blockchain_path: str
        :param blockchain: One of the Bitcoin compatible blockchains.
        :type blockchain: BLOCKCHAIN
        """

        self._blockchain_path = blockchain_path
        self._blockchain = blockchain

    def parse_and_extract_blockchain(self, database: Database) -> None:
        """Parse the blockchain with the previously constructed options
        :param database: Database to be written into.
        :type database: Database
        """

        blockchain = Blockchain(
            os.path.expanduser(str(self._blockchain_path) + "/blocks")
        )
        height = 0
        total_txs = 0
        ignored_tx_inputs = 0
        tx_inputs = 0
        ignored_tx_outputs = 0
        tx_outputs = 0

        context = zmq.Context()
        database_event_sender = context.socket(zmq.PAIR)
        database_event_receiver = context.socket(zmq.PAIR)
        database_event_sender.bind("inproc://bitcoin_dbbridge")
        database_event_receiver.connect("inproc://bitcoin_dbbridge")

        writer = DatabaseWriter(database, database_event_receiver, self._blockchain)
        writer.start()

        print(
            "commencing bitcoin parsing of "
            + str(self._blockchain_path)
            + "/blocks/index"
        )

        for block in blockchain.get_ordered_blocks(
            os.path.expanduser(str(self._blockchain_path.absolute()) + "/blocks/index"),
        ):
            height += 1
            for (tx_index, tx) in enumerate(block.transactions):
                total_txs += 1
                c_tx: CTransaction = CTransaction.deserialize(tx.hex)
                for (input_index, input) in enumerate(c_tx.vin):
                    tx_inputs += 1
                    if len(input.scriptSig) < 2:
                        # print("input is too small, ignoring")
                        ignored_tx_inputs += 1
                        continue
                    if is_p2pk_scriptsig(input.scriptSig):
                        # print("input is p2pk, ignoring")
                        ignored_tx_inputs += 1
                        continue
                    if is_p2pkh_scriptsig(input.scriptSig):
                        # print("input is p2pkh, ignoring")
                        ignored_tx_inputs += 1
                        continue
                    if is_p2sh_p2ms_scriptsig(input.scriptSig):
                        # print("input is p2sh(p2ms), ignoring")
                        ignored_tx_inputs += 1
                        continue
                    if is_p2sh_p2wpkh_scriptsig(input.scriptSig):
                        # print("input is p2sh(p2wpkh), ignoring")
                        ignored_tx_inputs += 1
                        continue

                    database_event_sender.send_pyobj(
                        BitcoinDataMessage(
                            input.scriptSig,
                            tx.txid,
                            DATATYPE.SCRIPT_SIG,
                            block.height,
                            input_index,
                        )
                    )

                for (output_index, output) in enumerate(c_tx.vout):
                    tx_outputs += 1
                    if is_p2pkh_output(output.scriptPubKey):
                        # print("output is p2pkh, ignoring")
                        ignored_tx_outputs += 1
                        continue
                    if is_p2pk_output(output.scriptPubKey):
                        # print("output is p2pk, ignoring")
                        ignored_tx_outputs += 1
                        continue
                    if is_p2sh_output(output.scriptPubKey):
                        # print("output is p2sh, ignoring")
                        ignored_tx_outputs += 1
                        continue
                    if is_p2ms_output(output.scriptPubKey):
                        # print("output is p2ms, ignoring")
                        ignored_tx_outputs += 1
                        continue
                    if is_p2wpkh_output(output.scriptPubKey):
                        # print("output is p2wpkh, ignoring")
                        ignored_tx_outputs += 1
                        continue
                    if is_p2wsh_output(output.scriptPubKey):
                        # print("output is p2wsh, ignoring")
                        ignored_tx_outputs += 1
                        continue
                    if is_p2tr_output(output.scriptPubKey):
                        # print("output is p2tr, ignoring")
                        ignored_tx_outputs += 1
                        continue

                    # print("nonstandard output:", output)
                    database_event_sender.send_pyobj(
                        BitcoinDataMessage(
                            output.scriptPubKey,
                            tx.txid,
                            DATATYPE.SCRIPT_PUBKEY,
                            block.height,
                            output_index,
                        )
                    )

            if height % 500 == 0:
                print(
                    "bitcoin parsed until height:",
                    height,
                    "n inputs:",
                    tx_inputs,
                    "n ignored inputs:",
                    ignored_tx_inputs,
                    "n outputs:",
                    tx_outputs,
                    "n ignored outputs:",
                    ignored_tx_outputs,
                )

        print("Completed blockchain parsing, commencing UTXO parsing")

        utxo_counter = 0
        for utxo in UTXOIterator(path=self._blockchain_path):
            utxo_counter += 1
            if utxo_counter % 1000 == 0:
                print(utxo_counter)
            print("out data:", utxo["out"]["data"], "txid:", utxo["tx_id"])
            database_event_sender.send_pyobj(
                BitcoinDataMessage(
                    utxo["out"]["data"],
                    utxo["tx_id"],
                    DATATYPE.SCRIPT_PUBKEY,
                    utxo["height"],
                    utxo["index"],
                )
            )

        print("Completed UTXO parsing")
