from typing import Optional, Dict
from database import COIN, DATATYPE, Database
from ethereum_blockchain_iterator import (
    ParseEthereumBlockBodies,
    ParseEthereumBlockHeaders,
)
from parser import CoinParser

ERC20_TRANSFER_METHOD_ID = bytes.fromhex("a9059cbb")
ERC20_APPROVE_METHOD_ID = bytes.fromhex("095ea7b3")
ERC20_TRANSFER_FROM_METHOD_ID = bytes.fromhex("23b872dd")
ETH_LEADING_12_ZERO_BYTES = bytes.fromhex("0"*24)

def check_if_template_contract_call(tx_data: bytes) -> bool:
    if len(tx_data) < 5:
        return False

    # transfer(address _to, uint256 _value) method_id: 0xa9059cbb
    # approve(address _spender, uint256 _value) method_id: 0x095ea7b3
    if tx_data[0:4] == ERC20_TRANSFER_METHOD_ID or tx_data[0:4] == ERC20_APPROVE_METHOD_ID:
        # the length of these contract calls is exactly 68 bytes
        if len(tx_data) != 68:
            return False
        # check that the address is present, by checking the number of zeroes
        if not (tx_data[4:16] == ETH_LEADING_12_ZERO_BYTES):
            return False
        return True
    # transferFrom(address _from, address _to, uint256 _value)
    if tx_data[0:4] == ERC20_TRANSFER_FROM_METHOD_ID:
        # the length of this contract call is exactly 100 bytes
        if len(tx_data) != 100:
            return False
        # check that the addresses are present, by checking the number of zeroes
        if not (tx_data[4:16] == ETH_LEADING_12_ZERO_BYTES and tx_data[36:48] == ETH_LEADING_12_ZERO_BYTES):
           return False
        return True
    return False


class EthereumParser(CoinParser):
    def __init__(self, chaindata_path: str, coin: COIN):
        """
        :param blockchain_path: Path to the Bitcoin blockchain (e.g. /home/user/.ethereum/geth/chaindata).
        :type blockchain_path: str
        :param coin: One of the Bitcoin compatible coins.
        :type coin: COIN
        """
        self.chaindata_path = chaindata_path + "/geth/chaindata"
        self.ancient_chaindata_path = self.chaindata_path + "/ancient"
        self.coin = coin

    def parse_blockchain(self, database: Optional[Database]) -> None:
        for height, block_body in enumerate(
            ParseEthereumBlockBodies(self.ancient_chaindata_path, self.chaindata_path)
        ):
            for (tx_index, tx) in enumerate(block_body.Transactions):
                if len(tx.data) < 2:
                    continue
                if check_if_template_contract_call(tx.data):
                    continue

                if database is not None:
                    database.insert_record(
                        tx.data,
                        tx.hash(),
                        self.coin,
                        DATATYPE.TX_DATA,
                        height,
                        0,
                    )

            if height == 50000:
                return

        for height, header in enumerate(
            ParseEthereumBlockHeaders(self.ancient_chaindata_path, self.chaindata_path)
        ):
            if len(header.Extra) > 0:
                print(height, header.Extra)
