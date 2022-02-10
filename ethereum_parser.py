from typing import Optional
from database import COIN, Database
from ethereum_blockchain_iterator import (
    ParseEthereumBlockBodies,
    ParseEthereumBlockHeaders,
)
from parser import CoinParser


class EthereumParser(CoinParser):
    def __init__(self, chaindata_path: str, coin: COIN):
        """
        :param blockchain_path: Path to the Bitcoin blockchain (e.g. /home/user/.ethereum/geth/chaindata).
        :type blockchain_path: str
        :param coin: One of the Bitcoin compatible coins.
        :type coin: COIN
        """
        self.chaindata_path = chaindata_path
        self.ancient_chaindata_path = chaindata_path + "/ancient"
        self.coin = coin

    def parse_blockchain(self, database: Optional[Database]):
        for height, block_body in enumerate(
            ParseEthereumBlockBodies(self.ancient_chaindata_path, self.chaindata_path)
        ):
            for (tx_index, tx) in enumerate(block_body.Transactions):
                if len(tx.data) > 0:
                    print(height, tx)

        for height, header in enumerate(
            ParseEthereumBlockHeaders(self.ancient_chaindata_path, self.chaindata_path)
        ):
            if len(header.Extra) > 0:
                print(height, header.Extra)


chaindata_path = "/home/drgrid/.ethereum/geth/chaindata"
ancient_chaindata_path = "/home/drgrid/.ethereum/geth/chaindata/ancient"

ethereum_parser = EthereumParser(chaindata_path, COIN.ETHEREUM_MAINNET)
ethereum_parser.parse_blockchain(None)
