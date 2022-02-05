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
    # Checks if the data is a DER encoded ECDSA signature
    # https://bitcoin.stackexchange.com/questions/92680/what-are-the-der-signature-and-sec-format
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
    if pubkey[0] == 0x02 or pubkey[0] == 0x03:
        return len(pubkey) == 33
    if pubkey[0] == 0x04:
        return len(pubkey) == 65
    return False

def is_pubkeys(pubkeys: bytes, number_of_keys: int) -> bool:
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
    """
        checks if the input script of the form:
            <sig>
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
    """
        checks if the input script of the form:
            <sig> <pubkey>
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
    """ 
        checks if the input script of the form: 
            OP_0 <sigs> OP_N <pubkeys> OP_N OP_CHECKMULTISIG 
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
    """
        checks if the input script of the form:
            OP_O <hash>
    """
    if len(script) != 23:
        return False
    if not script[1] == 0x00:
        return False
    return True

def is_p2pkh_output(script: bitcoin.core.script.CScript) -> bool:
    """
        checks if the output script is of the form:
            OP_DUP OP_HASH160 <hash> OP_EQUALVERIFY OP_CHECKSIG
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
    """
        checks if the output script is of the form:
            <pubkey> OP_CHECKSIG
    """
    if len(script) < 33:
        return False
    return (
        is_pubkey(script[1:-1]) and script[-1] == bitcoin.core.script.OP_CHECKSIG
    )

def is_p2sh_output(script: bitcoin.core.script.CScript) -> bool:
    """
        checks if the output script is of the form:
            OP_HASH160 <hash> OP_EQUAL
    """
    if len(script) != 23:
        return False
    return (
        script[0] == bitcoin.core.script.OP_HASH160 and script[-1] == bitcoin.core.script.OP_EQUAL
    )

def is_p2ms_output(script: bitcoin.core.script.CScript) -> bool:
    """
        checks if the output script is of the form:
            OP_N <pubkeys> OP_N OP_CHECKMULTISIG
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

        
class BitcoinParser(CoinParser):
    def __init__(self, blockchain_path: str, coin: COIN):
        self.blockchain_path = blockchain_path
        self.coin = coin

    def pre_filter(self, c_tx): 
        print(c_tx)
    
    def parse_blockchain_test(self):
        blockchain = Blockchain(os.path.expanduser(self.blockchain_path))
        height = 0
        total_txs = 0
        ignored_tx_inputs = 0
        tx_inputs = 0
        ignored_tx_outputs = 0
        tx_outputs = 0
        for block in blockchain.get_ordered_blocks(os.path.expanduser(self.blockchain_path + '/index'), end=2100000):
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
                    print("nonstandard output:", output)

        print(height, tx_index, input_index, total_txs, tx_inputs, ignored_tx_inputs, len(input.scriptSig), input.scriptSig)
        print(height, tx_outputs, ignored_tx_outputs)


        #    if height == 100000:
        #        print(height, tx_index, input_index, total_txs, tx_inputs, ignored_tx_inputs, len(input.scriptSig), input.scriptSig)
        #        print(height, tx_outputs, ignored_tx_outputs)

        #        return


    def parse_blockchain(self, filter: Callable[[bytes, Optional[int]], str], database: Optional[Database]):

        blockchain = Blockchain(os.path.expanduser(
            self.blockchain_path))
        for block in blockchain.get_ordered_blocks(os.path.expanduser(self.blockchain_path + '/index'), end=1000):
            for tx in block.transactions:
                c_tx = bitcoin.core.CTransaction.deserialize(tx.hex)
                # do some simple OP_RETURN detection
                for (index, output) in enumerate(c_tx.vout):
                    if detectors.bitcoin_detect_op_return_output(output.scriptPubKey):
                        if database:
                            database.insert_record(output.scriptPubKey, tx.txid,
                                                   self.coin, DATATYPE.SCRIPT_PUBKEY, block.height, index)

                for (index, input) in enumerate(c_tx.vin):
                    detected_file = detectors.bitcoin_find_file_with_imghdr(
                        input.scriptSig)
                    if len(detected_file) > 0:
                        if database:
                            database.insert_record(input.scriptSig, tx.txid, self.coin,
                                                   DATATYPE.SCRIPT_SIG, block.height, index)
                        continue

                    detected_text = detectors.gnu_strings(input.scriptSig, 4)
                    if detected_text:
                        if database:
                            database.insert_record(input.scriptSig, tx.txid,
                                                   self.coin, DATATYPE.SCRIPT_SIG, block.height, index)
