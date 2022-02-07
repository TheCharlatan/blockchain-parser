from blockchain_parser.blockchain import Blockchain
from database import COIN, DATATYPE, Database
import detectors
from parser import CoinParser
import bitcoin.rpc
from typing import Callable, Optional
import os

opcode_counters = {
    bitcoin.core.script.OP_1: 1, 
    bitcoin.core.script.OP_2: 2, 
    bitcoin.core.script.OP_3: 3, 
    bitcoin.core.script.OP_4: 4, 
    bitcoin.core.script.OP_5: 5, 
    bitcoin.core.script.OP_6: 6, 
    bitcoin.core.script.OP_7: 7, 
    bitcoin.core.script.OP_8: 8, 
    bitcoin.core.script.OP_9: 9, 
    bitcoin.core.script.OP_10: 10,
    bitcoin.core.script.OP_11: 11,
    bitcoin.core.script.OP_12: 12,
    bitcoin.core.script.OP_13: 13,
    bitcoin.core.script.OP_14: 14,
    bitcoin.core.script.OP_15: 15,
    bitcoin.core.script.OP_16: 16,
}

def is_DER_sig(sig: bytes) -> bool:
    """ Checks if the data is a DER encoded ECDSA signature
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
    if sig[3+len_r+1] != 0x02:
        return False
    len_s = sig[3+len_r+2]

    # The last extra byte is the sighash flag
    computed_len = 4 + len_r + 2 + len_s + 1
    if len(sig) != computed_len:
        False
    return True

def is_pubkey(pubkey: bytes) -> bool:
    """ Checks if the data is a SEC serialized ECDSA public key
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
    """ Checks if the data are multiple SEC serialized ECDSA public keys
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
        if pubkeys[pos] ==0x02 or pubkeys[pos] == 0x03:
            pos += 34
        elif pubkeys[pos] == 0x04:
            pos += 66
        else:
            return False
    return True

def is_p2pk_scriptsig(script: bitcoin.core.script.CScript) -> bool:
    """ Checks if the input script of the form:
            <sig>
    :param script: Script to be analyzed.
    :type script: bitcoin.core.script.CScript
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
    return  is_p2pk

def is_p2pkh_scriptsig(script: bitcoin.core.script.CScript) -> bool:
    """ Checks if the input script of the form:
            <sig> <pubkey>
    :param script: Script to be analyzed.
    :type script: bitcoin.core.script.CScript
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

def is_p2sh_p2ms_scriptsig(script: bitcoin.core.script.CScript) -> bool:
    """ Checks if the input script of the form: 
            OP_0 <sigs> OP_N <pubkeys> OP_N OP_CHECKMULTISIG 
    :param script: Script to be analyzed.
    :type script: bitcoin.core.script.CScript
    :return: True if the passed in bitcoin CScript is a p2sh(p2ms) input script.
    :rtype: bool
    """

    # P2SH inputs always start with OP_0
    if len(script) < 96:
        return False
    for (elem_index, elem) in enumerate(script):
        # This is pushed because of the P2MS bug: it always requires an extra element on the stack
        if elem == 0x00 and elem_index == 0:
            continue
        if type(elem) is not bytes:
            return False
        # Check the redeem script for p2ms
        if elem[0] in opcode_counters.keys():
            if elem[-1] != bitcoin.core.script.OP_CHECKMULTISIG:
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

def is_p2sh_p2wpkh_scriptsig(script: bitcoin.core.script.CScript) -> bool:
    """ Checks if the input script of the form:
            OP_O <hash>
    :param script: Script to be analyzed.
    :type script: bitcoin.core.script.CScript
    :return: True if the passed in bitcoin CScript is a p2sh(p2wpkh) input script.
    :rtype: bool
    """

    if len(script) != 23:
        return False
    if not script[1] == 0x00:
        return False
    return True

def is_p2pkh_output(script: bitcoin.core.script.CScript) -> bool:
    """ Checks if the output script is of the form:
            OP_DUP OP_HASH160 <hash> OP_EQUALVERIFY OP_CHECKSIG
    :param script: Script to be analyzed.
    :type script: bitcoin.core.script.CScript
    :return: True if the passed in bitcoin CScript is a p2pkh output script.
    :rtype: bool
    """

    if len(script) != 25:
        return False
    return (
        script[0] == bitcoin.core.script.OP_DUP
        and script[1] == bitcoin.core.script.OP_HASH160
        and script[23] == bitcoin.core.script.OP_EQUALVERIFY
        and script[24] == bitcoin.core.script.OP_CHECKSIG
    )

def is_p2pk_output(script: bitcoin.core.script.CScript) -> bool:
    """ Checks if the output script is of the form:
            <pubkey> OP_CHECKSIG
    :param script: Script to be analyzed.
    :type script: bitcoin.core.script.CScript
    :return: True if the passed in bitcoin CScript is a p2pk output script.
    :rtype: bool
    """

    if len(script) < 33:
        return False
    return (
        is_pubkey(script[1:-1]) and script[-1] == bitcoin.core.script.OP_CHECKSIG
    )

def is_p2sh_output(script: bitcoin.core.script.CScript) -> bool:
    """ Checks if the output script is of the form:
            OP_HASH160 <hash> OP_EQUAL
    :param script: Script to be analyzed.
    :type script: bitcoin.core.script.CScript
    :return: True if the passed in bitcoin CScript is a p2sh output script.
    :rtype: bool
    """

    if len(script) != 23:
        return False
    return (
        script[0] == bitcoin.core.script.OP_HASH160 and script[-1] == bitcoin.core.script.OP_EQUAL
    )

def is_p2ms_output(script: bitcoin.core.script.CScript) -> bool:
    """ Checks if the output script is of the form:
            OP_N <pubkeys> OP_N OP_CHECKMULTISIG
    :param script: Script to be analyzed.
    :type script: bitcoin.core.script.CSCript
    :return: True if the passed in bitcoin CScript is a p2ms output script.
    :rtype: bool
    """

    if len(script) < 33:
        return False
    if script[0] not in opcode_counters.keys():
        return False
    if script[-2] not in opcode_counters.keys():
        return False
    num_pubkeys = opcode_counters[script[-2]]
    if not is_pubkeys(script[2:-2], num_pubkeys):
        return False
    return script[-1] == bitcoin.core.script.OP_CHECKMULTISIG

def is_p2wpkh_output(script: bitcoin.core.script.CScript) -> bool:
    """ Checks if the output script if of the form:
            OP_0 <pubkey hash>
    :param script: Script to be analyzed.
    :type script: bitcoin.core.script.CScript
    :return: True if the passed in bitcoin CScript is a p2wpkh output script.
    :rtype: bool
    """

    if len(script) != 22:
        return False
    return script[0] == OP_0

def is_p2wsh_output(script: bitcoin.core.script.CSCript) -> bool:
    """ Checks if the output script if of the form:
            OP_0 <script hash>
    :param script: Script to be analyzed.
    :type script: bitcoin.core.script.CScript
    :return: True if the passed in bitcoin CScript is a p2wsh output script.
    :rtype: bool
    """

    if len(script) != 34:
        return False
    return script[0] == OP_0

def is_p2tr_output(script: bitcoin.core.script.CSCript) -> bool:
    """ Checks if the output script if of the form:
            OP_1 <x only pubkey>
    :param script: Script to be analyzed.
    :type script: bitcoin.core.script.CScript
    :return: True if the passed in bitcoin CScript is a p2wtr output script.
    :rtype: bool
    """

    if len(script) != 34:
        return False
    return script[0] == OP_1



        
class BitcoinParser(CoinParser):
    def __init__(self, blockchain_path: str, coin: COIN):
        """
        :param blockchain_path: Path to the Bitcoin blockchain (e.g. /home/user/.bitcoin/).
        :type blockchain_path: str
        :param coin: One of the Bitcoin compatible coins.
        :type coin: COIN
        """

        self.blockchain_path = blockchain_path
        self.coin = coin

    def parse_blockchain(self, database: Optional[Database]):
        """ Parse the blockchain with the previously constructed options
        :param database: Database to be written into.
        :type database: Database
        """

        blockchain = Blockchain(os.path.expanduser(self.blockchain_path + '/blocks'))
        height = 0
        total_txs = 0
        ignored_tx_inputs = 0
        tx_inputs = 0
        ignored_tx_outputs = 0
        tx_outputs = 0
        for block in blockchain.get_ordered_blocks(os.path.expanduser(self.blockchain_path + '/blocks/index'), end=2100000):
            height += 1
            for (tx_index, tx) in enumerate(block.transactions):
                total_txs += 1
                c_tx = bitcoin.core.CTransaction.deserialize(tx.hex)
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

                    if database is not None:
                        database.insert_record(input.scriptSig, tx.txid, self.coin,
                            DATATYPE.SCRIPT_SIG, block.height, input_index)

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

                    if database is not None:
                        database.insert_record(output.scriptPubKey, tx.txid,
                            self.coin, DATATYPE.SCRIPT_PUBKEY, block.height, index)
        
        print(height, tx_index, input_index, total_txs, tx_inputs, ignored_tx_inputs, len(input.scriptSig), input.scriptSig)
        print(height, tx_outputs, ignored_tx_outputs)

        parse_ldb(database, coin=self.coin, btc_dir=self.blockchain_path)