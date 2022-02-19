from bitcoin_parser import BitcoinParser
from database import COIN, DATATYPE, Database
import detectors
import bitcoin.rpc
import binascii
import argparse

from monero_parser import MoneroParser


def unhexlify_str(h: str) -> bytes:
    return binascii.unhexlify(h.encode("ascii"))


if __name__ == "__main__":
    """Main function"""
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description="Tool for parsing and analysing various blockchain data",
    )
    parser.add_argument(
        "-m",
        "--monero-database",
        default="/home/drgrid/.bitmonero/lmdb",
        help="path to the monero block files",
    )
    parser.add_argument(
        "-b",
        "--bitcoin-database",
        default="/home/drgrid/.bitcoin/testnet3",
        help="path to the bitcoin block files",
    )
    parser.add_argument(
        "-d",
        "--database",
        default="test.db",
        help="name of the database used to store results",
    )

    # Parse the command line arguments
    args = parser.parse_args()

    # Create Bitcoin and Monero parsers
    monero_parser = MoneroParser(args.monero_database, COIN.MONERO_STAGENET)
    bitcoin_parser = BitcoinParser(args.bitcoin_database, COIN.BITCOIN_REGTEST)

    # Create a database handler
    database = Database(args.database)

    # Parse the blockchains
    # bitcoin_parser.parse_blockchain(database)
    monero_parser.parse_blockchain(database)

    # Retrieve and prine some results
    results = database.get_data(DATATYPE.SCRIPT_SIG)
    for result in results:
        for potential_string in result:
            print(detectors.gnu_strings(potential_string))
            print(
                detectors.bitcoin_find_file_with_imghdr(
                    bitcoin.core.CScript(potential_string)
                )
            )
