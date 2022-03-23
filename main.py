from pathlib import Path
from tkinter import N
from bitcoin_parser import BitcoinParser
from database import BLOCKCHAIN, Database, coinStringToCoin
import binascii
import argparse
from ethereum_parser import EthereumParser
from analyzer import Analyzer, Detector

from monero_parser import MoneroParser
from parser import DataExtractor

from view import View, ViewMode

def unhexlify_str(h: str) -> bytes:
    return binascii.unhexlify(h.encode("ascii"))


def parse(blockchain_raw: str, raw_coin_path: str, database_name: str) -> None:
    coin_path = Path(raw_coin_path)
    # Create a parser
    parser: DataExtractor
    if "bitcoin" in blockchain_raw:
        parser = BitcoinParser(
            coin_path, BLOCKCHAIN.BITCOIN_REGTEST)
    elif "ethereum" in blockchain_raw:
        parser = EthereumParser(
            coin_path, BLOCKCHAIN.ETHEREUM_MAINNET)
    elif "monero" in blockchain_raw:
        parser = MoneroParser(coin_path, BLOCKCHAIN.MONERO_STAGENET)
    else:
        raise BaseException("invalid blockchain argument in parse method")

    # Create a database handler
    database = Database(database_name)

    # Parse the blockchains
    parser.parse_and_extract_blockchain(database)
    return

def analyze(blockchain_raw: str, database_path: str, detector_raw: str) -> None:
    detector: Detector
    if detector_raw == "native_strings":
        detector = Detector.native_strings
    elif detector_raw == "gnu_strings":
        detector = Detector.gnu_strings
    elif detector_raw == "imghdr_files":
        detector = Detector.imghdr_files
    elif detector_raw == "magic_files":
        detector = Detector.magic_files
    else:
        raise BaseException("invalid detector argument for analyze")

    blockchain = coinStringToCoin(blockchain_raw)
    database = Database(database_path)
    analyzer = Analyzer(blockchain, database)
    analyzer.analyze(detector)
    return

def view(blockchain_raw: str, database_path: str, mode_raw: str) -> None:
    blockchain = coinStringToCoin(blockchain_raw)
    mode: ViewMode
    if mode_raw == "ascii_histogram":
        mode = ViewMode.ASCII_HISTOGRAM
    elif mode_raw == "magic_file_histogram":
        mode = ViewMode.MAGIC_FILE_HISTOGRAM
    elif mode_raw == "imghdr_file_histogram":
        mode = ViewMode.IMGHDR_FILE_HISTOGRAM
    database = Database(database_path)
    view = View(blockchain, database)
    view.view(mode)


if __name__ == "__main__":
    """Main function"""
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description="Tool for parsing and analysing various blockchain data",
    )
    parser.add_argument(
        "-d",
        "--database",
        default="test.db",
        help="name of the database used to store results",
    )
    parser.add_argument(
        "-b",
        "--blockchain",
        choices=("bitcoin_mainnet", "bitcoin_testnet3", "bitcoin_regtest", "monero_mainnet", "monero_stagenet", "monero_testnet", "ethereum_mainnet"),
        help="Blockchain to target. Required argument, only single targets are allowed."
    )
    parser.add_argument(
        "-p",
        "--parse",
        help="""Run the tool in parse mode to collect blockchain data, requires the blockchain data directory as argument, e.g
                ~/.ethereum
                ~/.bitmonero
                ~/.bitcoin
            """
    )
    parser.add_argument(
        "-a",
        "--analyze",
        help="Run the tool in analysis mode to detect specific data types",
        choices=("native_strings", "gnu_strings", "imghdr_files", "magic_files")
    )
    parser.add_argument(
        "-v",
        "--view",
        help="Run the to tool in view mode to further analysis",
        choices=("ascii_histogram", "magic_file_histogram", "imghdr_file_histogram")
    )

    # Parse the command line arguments
    args = parser.parse_args()

    if args.parse is not None:
        if args.blockchain is None:
            raise BaseException("require a blockchain argument for parse mode")
        parse(args.blockchain, args.parse, args.database)
    elif args.analyze is not None:
        analyze(args.blockchain, args.database, args.analyze)
    elif args.view is not None:
        view(args.blockchain, args.database, args.view)
    else:
        raise BaseException("require a mode to run in")
