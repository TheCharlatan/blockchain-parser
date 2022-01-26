import os
from blockchain_parser.blockchain import Blockchain
from bitcoin_parser import BitcoinParser
from database import COIN, DATATYPE, Database
import detectors
import enum
import bitcoin.rpc
import binascii

from monero_parser import MoneroParser


def unhexlify_str(h: str) -> bytes:
    return binascii.unhexlify(h.encode('ascii'))


if __name__ == '__main__':
    monero_parser = MoneroParser("/home/drgrid/.bitmonero/stagenet/lmdb")
    bitcoin_parser = BitcoinParser(
        "~/.bitcoin/regtest/blocks", COIN.BITCOIN_REGTEST)
    database = Database("test.db")

    results = database.get_data(DATATYPE.SCRIPT_SIG)
    for result in results:
        for potential_string in result:
            print(detectors.gnu_strings(potential_string))
            print(detectors.bitcoin_find_file_with_imghdr(
                bitcoin.core.CScript(potential_string)))
