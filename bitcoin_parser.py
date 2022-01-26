from blockchain_parser.blockchain import Blockchain
from database import COIN, DATATYPE, Database
import detectors
from parser import CoinParser
import bitcoin.rpc
from typing import Callable, Optional
import os


class BitcoinParser(CoinParser):
    def __init__(self, blockchain_path: str, coin: COIN):
        self.blockchain_path = blockchain_path
        self.coin = coin

    def parse_blockchain(self, filter: Callable[[bytes, Optional[int]], str], database: Optional[Database]):

        blockchain = Blockchain(os.path.expanduser(
            self.blockchain_path))
        for block in blockchain.get_ordered_blocks(os.path.expanduser(self + '/index'), end=1000):
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
