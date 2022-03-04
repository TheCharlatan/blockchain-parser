from tkinter import N
from bitcoin_parser import BitcoinParser
from database import COIN, DATATYPE, Database, coinStringToCoin
import binascii
import argparse
from ethereum_parser import EthereumParser
from detectors import Detector

from monero_parser import MoneroParser
from parser import CoinParser


def unhexlify_str(h: str) -> bytes:
    return binascii.unhexlify(h.encode("ascii"))


def parse(coin: str, coin_path: str, database: str):
    # Create a parser
    parser = CoinParser
    if "bitcoin" in coin:
        parser = BitcoinParser(
            coin_path, COIN.BITCOIN_REGTEST)
    elif "ethereum" in coin:
        parser = EthereumParser(
            coin_path, COIN.ETHEREUM_MAINNET)
    elif "monero" in coin:
        parser = MoneroParser(coin_path, COIN.MONERO_STAGENET)
    else:
        raise "invalid coin argument"

    # Create a database handler
    database = Database(database)

    # Parse the blockchains
    parser.parse_blockchain(database)
    return

def analyze(coin: str, database: str):
    coin = coinStringToCoin(coin)
    database = Database(database)
    analyzer = Detector(coin, database)
    analyzer.analyze()
    return


if __name__ == "__main__":
    """Main function"""
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description="Tool for parsing and analysing various blockchain data",
    )
    parser.add_argument(
        "-i",
        "--data-dir",
        default="/home/drgrid/.bitcoin",
        help = """Path the coin data directory, e.g. 
            /home/drgrid.ethereum | 
            home/drgrid/.bitmonero | 
            /home/drgrid/.bitcoin
            """
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
            bitcoin_mainnet   |
            bitcoin_testnet3   |
            bitcoin_regtest   |
            monero_mainnet   |
            monero_stagnet   |
            monero_testnet   |
            ethereum_mainnet
            """
    )
    parser.add_argument(
        "-o",
        "--mode",
        default="parse",
        help="""Mode of operation, either parses or analyzes data. Valid arguments are: \n
            parse   |
            analyze   |
            view
            """
    )

    # Parse the command line arguments
    args = parser.parse_args()

    if args.mode == "parse":
        parse(args.coin, args.data_dir, args.database)
    elif args.mode == "analyze":
        analyze(args.coin, args.database)
    elif args.mode == "view":
        raise "view mode not implemented yet"
    else:
        raise "require a mode to run in"

    # Retrieve and prine some results
    # results = database.get_data(DATATYPE.SCRIPT_SIG)
    # for result in results:
    #     for potential_string in result:
    #         print(detectors.gnu_strings(potential_string))
    #         print(
    #             detectors.bitcoin_find_file_with_imghdr(
    #                 bitcoin.core.CScript(potential_string)
    #             
    #         )
