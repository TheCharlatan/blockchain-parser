from pathlib import Path
from tkinter import N
from bitcoin_parser import BitcoinParser
from database import BLOCKCHAIN, DATATYPE, Database, coinStringToCoin
import binascii
import argparse
from ethereum_parser import EthereumParser
from detector import Detector

from monero_parser import MoneroParser
from parser import DataExtractor


def unhexlify_str(h: str) -> bytes:
    return binascii.unhexlify(h.encode("ascii"))


def parse(blockchain: str, coin_path: str, database: str):
    coin_path = Path(coin_path)
    # Create a parser
    parser = DataExtractor
    if "bitcoin" in blockchain:
        parser = BitcoinParser(
            coin_path, BLOCKCHAIN.BITCOIN_REGTEST)
    elif "ethereum" in blockchain:
        parser = EthereumParser(
            coin_path, BLOCKCHAIN.ETHEREUM_MAINNET)
    elif "monero" in blockchain:
        parser = MoneroParser(coin_path, BLOCKCHAIN.MONERO_STAGENET)
    else:
        raise "invalid coin argument"

    # Create a database handler
    database = Database(database)

    # Parse the blockchains
    parser.parse_and_extract_blockchain(database)
    return

def analyze(blockchain: str, database_path: str):
    blockchain = coinStringToCoin(blockchain)
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
        "-b",
        "--blockchain",
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
        "-m",
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
    path = args.data_dir

    if args.mode == "parse":
        parse(args.blockchain, args.data_dir, args.database)
    elif args.mode == "analyze":
        analyze(args.blockchain, args.database)
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
