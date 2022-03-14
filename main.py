from pathlib import Path
from tkinter import N
from bitcoin_parser import BitcoinParser
from database import BLOCKCHAIN, Database, coinStringToCoin
import binascii
import argparse
from ethereum_parser import EthereumParser
from detector import Detector

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

def analyze(blockchain_raw: str, database_path: str) -> None:
    blockchain = coinStringToCoin(blockchain_raw)
    database = Database(database_path)
    analyzer = Detector(blockchain, database)
    analyzer.analyze()
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
        default="bitcoin_mainnet",
        coices=("bitcoin_mainnet", "bitcoin_testnet3", "bitcoin_regtest", "monero_mainnet", "monero_stagenet", "monero_testnet", "ethereum_mainnet"),
        help="Coin to target. Required argument, only single targets are allowed."
    )
    parser.add_argument(
        "-p",
        "--parse",
        default="/home/drgrid/.bitcoin",
        help="""Run the tool in parse mode to collect blockchain data, requires the blockchain data directory as argument, e.g
                /home/drgrid/.ethereum
                /home/drgrid/.bitmonero
                /home/drgrid/.bitcoin
            """
    )
    parser.add_argument(
        "-a",
        "--analyze",
        help="Run the tool in analysis mode to detect specific data types",
        choices=("ascii", "files")
    )
    parser.add_argument(
        "-v",
        "--view",
        action="store_true",
        help="Run the to tool in view mode to further analysis"
    )
    parser.add_argument(
        "-c",
        "--criteria",
        default="ascii",
        help="""analysis criteria to run against. Valid arguments are: \n
            ascii |
            files"""
    )

    # Parse the command line arguments
    args = parser.parse_args()
    path = args.data_dir

    if args.parse is not None or args.parse is True:
        parse(args.blockchain, args.parse, args.database)
    if args.analyze == "acsii" or args.analyze == "files":
        analyze(args.blockchain, args.database)
    elif args.view:
        raise BaseException("view mode not implemented yet")
    else:
        raise BaseException("require a mode to run in")

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
