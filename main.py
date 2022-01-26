from bitcoin_parser import BitcoinParser
from database import COIN, DATATYPE, Database
import detectors
import bitcoin.rpc
import binascii
import argparse

from monero_parser import MoneroParser


def unhexlify_str(h: str) -> bytes:
    return binascii.unhexlify(h.encode('ascii'))


if __name__ == '__main__':
    """Main function"""
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description="Tool for parsing and analysing various blockchain data")
    parser.add_argument("-m",  "--monero-database",
                        default="/home/drgrid/.bitmonero/stagenet/lmdb", help="path to the monero block files")
    parser.add_argument("-b", "--bitcoin-database",
                        default="~/.bitcoin/regtest/blocks", help="path to the bitcoin block files")
    parser.add_argument("-d", "--database", default="test.db",
                        help="name of the database used to store results")

    args = parser.parse_args()

    monero_parser = MoneroParser(args.monero_database)
    bitcoin_parser = BitcoinParser(
        args.bitcoin_database, COIN.BITCOIN_REGTEST)
    database = Database(args.database)

    results = database.get_data(DATATYPE.SCRIPT_SIG)
    for result in results:
        for potential_string in result:
            print(detectors.gnu_strings(potential_string))
            print(detectors.bitcoin_find_file_with_imghdr(
                bitcoin.core.CScript(potential_string)))
