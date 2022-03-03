from bitcoin_parser import BitcoinParser
from database import COIN, DATATYPE, Database
import detectors
import bitcoin.rpc
import binascii
import argparse
from ethereum_parser import EthereumParser

from monero_parser import MoneroParser
from parser import CoinParser


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
        "--monero-path",
        default="/home/drgrid/.bitmonero/lmdb",
        help="path to the monero data directory",
    )
    parser.add_argument(
        "-b",
        "--bitcoin-path",
        default="/home/drgrid/.bitcoin",
        help="path to the bitcoin data directory",
    )
    parser.add_argument(
        "-e",
        "--ethereum-path",
        default="/home/drgrid/.ethereum",
        help="path to the ethereum data directory",
    )
    parser.add_argument(
        "-d",
        "--database",
        default="test.db",
        help="name of the database used to store results",
    )
    parser.add_argument(
        "-c",
        "--coin",
        default="bitcoin_mainnet",
        help="""Coin to target. Only single targets are allowed, valid targets are: \n
            bitcoin_mainnet \n
            bitcoin_testnet3 \n
            bitcoin_regtest \n
            monero_mainnet \n
            monero_stagnet \n
            monero_testnet \n
            ethereum_mainnet \n
            """
    )

    # Parse the command line arguments
    args = parser.parse_args()

    # Create a parser
    parser = CoinParser
    if "bitcoin" in args.coin:
        parser = BitcoinParser(
            args.bitcoin_path, COIN.BITCOIN_REGTEST)
    elif "ethereum" in args.coin:
        parser = EthereumParser(
            args.ethereum_path, COIN.ETHEREUM_MAINNET)
    elif "monero" in args.coin:
        monero_parser = MoneroParser(args.monero_path, COIN.MONERO_STAGENET)
    else:
        raise "invalid coin argument"

    # Create a database handler
    database = Database(args.database)

    # Parse the blockchains
    parser.parse_blockchain(database)
    # monero_parser.parse_blockchain(database)

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
