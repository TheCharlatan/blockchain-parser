import threading
from typing import NamedTuple

import zmq
from database import BLOCKCHAIN, DATATYPE, Database
from ethereum_blockchain_iterator import (
    ParseEthereumBlockBodies,
    ParseEthereumBlockHeaders,
)
from parser import DataExtractor
from pathlib import Path

ERC20_TRANSFER_METHOD_ID = bytes.fromhex("a9059cbb")
ERC20_APPROVE_METHOD_ID = bytes.fromhex("095ea7b3")
ERC20_TRANSFER_FROM_METHOD_ID = bytes.fromhex("23b872dd")
ETH_LEADING_12_ZERO_BYTES = bytes.fromhex("0"*24)

def check_if_template_contract_call(tx_data: bytes) -> bool:
    """"Checks if the provide tx_data contains one of the standard ERC20 function invocations
    :param tx_data: The tx data to be analyzed
    :type tx_data: bytes"""
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


class EthereumDataMessage(NamedTuple):
    """Named Tuple for the zmq message for writing prased and extracted data to the database"""
    data: bytes
    txid: bytes
    data_type: DATATYPE
    block_height: int


class DatabaseWriter(threading.Thread):
    """DatabaseWriter acts as a worker thread for writing to the sql database
    and receives from a zmq socket"""

    def __init__(self, database: Database, receiver: zmq.Socket, blockchain: BLOCKCHAIN):
        """
        :param database: Database to be written into
        :type database: Database
        :param receiver: Receives parsed extra bytes and monero transaction indices
        :type receiver: zmq.Socket
        :param blockchain: Some Ethereum-compatible blockchain
        :type blockchain: BLOCKCHAIN"""
        self._db = database
        self._receiver = receiver
        self._blockchain = blockchain
        threading.Thread.__init__(self)

    def run(self) -> None:
        records = []
        while True:
            message: EthereumDataMessage = self._receiver.recv_pyobj()

            records.append((
                message.data,
                message.txid,
                self._blockchain.value,
                message.data_type.value,
                message.block_height,
                0
            ))

            if len(records) > 500:
                print("ethereum writing to DB...", records[0])
                self._db.insert_records(records)
                records = []


class EthereumParser(DataExtractor):
    def __init__(self, chaindata_path: Path, blockchain: BLOCKCHAIN):
        """
        :param blockchain_path: Path to the Ethereum blockchain (e.g. /home/user/.ethereum/geth/chaindata).
        :type blockchain_path: str
        :param blockchain: One of the Ethereum compatible blockchains.
        :type blockchain: BLOCKCHAIN
        """
        self._chaindata_path = str(chaindata_path.expanduser()) + "/geth/chaindata"
        self._ancient_chaindata_path = self._chaindata_path + "/ancient"
        self._blockchain = blockchain

    def parse_and_extract_blockchain(self, database: Database) -> None:
        """Parse the blockchain with the previously constructed options
        :param database: Database to be written into.
        :type database: Database
        """
        context = zmq.Context()
        database_event_sender = context.socket(zmq.PAIR)
        database_event_receiver = context.socket(zmq.PAIR)
        database_event_sender.bind("inproc://ethereum_dbbridge")
        database_event_receiver.connect("inproc://ethereum_dbbridge")

        writer = DatabaseWriter(database, database_event_receiver, self._blockchain)
        writer.start()

        for height, block_body in enumerate(
            ParseEthereumBlockBodies(self._ancient_chaindata_path, self._chaindata_path)
        ):
            for (tx_index, tx) in enumerate(block_body.Transactions):
                if len(tx.data) < 2:
                    continue
                if check_if_template_contract_call(tx.data):
                    continue

                database_event_sender.send_pyobj(EthereumDataMessage(tx.data, tx.hash(), DATATYPE.TX_DATA, height))

        print("done parsing ethereum blocks, now parsing ethereum headers")

        for height, header in enumerate(
            ParseEthereumBlockHeaders(self._ancient_chaindata_path, self._chaindata_path)
        ):
            if len(header.Extra) > 0:
                database_event_sender.send_pyobj(EthereumDataMessage(header.Extra, header.TxHash, DATATYPE.TX_DATA, height))

        print("\n\n Completed Ethereum Parsing \n\n")
