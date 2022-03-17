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

def unhexlify_str(h: str) -> bytes:
    return binascii.unhexlify(h.encode("ascii"))


def parse(blockchain: str, raw_coin_path: str, database_name: str) -> None:
    coin_path = Path(raw_coin_path)
    # Create a parser
    parser: DataExtractor
    if "bitcoin" in blockchain:
        parser = BitcoinParser(
            coin_path, BLOCKCHAIN.BITCOIN_REGTEST)
    elif "ethereum" in blockchain:
        parser = EthereumParser(
            coin_path, BLOCKCHAIN.ETHEREUM_MAINNET)
    elif "monero" in blockchain:
        parser = MoneroParser(coin_path, BLOCKCHAIN.MONERO_STAGENET)
    else:
        raise BaseException("invalid coin argument in parse method")

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
    elif detector_raw == "files":
        detector = Detector.files
    else:
        raise BaseException("invalid detector argument for analyze")

    blockchain = coinStringToCoin(blockchain_raw)
    database = Database(database_path)
    analyzer = Analyzer(blockchain, database)
    analyzer.analyze(detector)
    return


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
        help="Coin to target. Required argument, only single targets are allowed."
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
        choices=("native_strings", "gnu_strings", "files")
    )
    parser.add_argument(
        "-v",
        "--view",
        action="store_true",
        help="Run the to tool in view mode to further analysis"
    )


    # Parse the command line arguments
    args = parser.parse_args()

    if args.parse is not None:
        if args.blockchain is None:
            raise BaseException("require a blockchain argument for parse mode")
        parse(args.blockchain, args.parse, args.database)
    elif args.analyze == "acsii" or args.analyze == "files":
        analyze(args.blockchain, args.database, args.analyze)
    elif args.view:
        raise BaseException("view mode not implemented yet")
    else:
        raise BaseException("require a mode to run in")

    # Retrieve and print some results
    # results = database.get_data(DATATYPE.SCRIPT_SIG)
    # for result in results:
    #     for potential_string in result:
    #         print(detectors.gnu_strings(potential_string))
    #         print(
    #             detectors.bitcoin_find_file_with_imghdr(
    #                 bitcoin.core.CScript(potential_string)
    #             
    #         )
