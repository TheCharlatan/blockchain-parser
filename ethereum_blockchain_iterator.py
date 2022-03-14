from __future__ import annotations
from typing import Union
from ethereum_freezer_tables import FreezerBodiesTable, FreezerHeadersTable
from ethereum_leveldb_tables import EthLevelDB
from ethereum_rlp import Body, Header


class ParseEthereumBlockHeaders:
    def __init__(self, ancient_chaindata_path: str, chaindata_path: str):
        self.eth_freezer_table = FreezerHeadersTable(ancient_chaindata_path)
        self.eth_leveldb = EthLevelDB(chaindata_path)
        self.value = 0

    def get_header(self, number: int) -> Header:
        try:
            header: Union[Header, None] = self.eth_freezer_table.get_header_by_height(number)
        except:
            header = self.eth_leveldb.get_header_by_height(number)
        if header is None:
            raise Exception(f"header not found for block height: {number}")
        return header

    def __iter__(self) -> ParseEthereumBlockHeaders:
        return self

    def __next__(self) -> Header:
        try:
            header = self.get_header(self.value + 1)
        except:
            raise StopIteration
        self.value += 1
        return header


class ParseEthereumBlockBodies:
    def __init__(self, ancient_chaindata_path: str, chaindata_path: str):
        self.eth_freezer_table = FreezerBodiesTable(ancient_chaindata_path)
        self.eth_leveldb = EthLevelDB(chaindata_path)
        self.value = 0

    def get_body(self, number: int) -> Body:
        try:
            body: Union[Body, None] = self.eth_freezer_table.get_body_by_height(number)
        except:
            body = self.eth_leveldb.get_body_by_height(number)
        if body is None:
            raise Exception(f"body not found for block height: {number}")
        return body

    def __iter__(self) -> ParseEthereumBlockBodies:
        return self

    def __next__(self) -> Body:
        try:
            body = self.get_body(self.value + 1)
        except:
            raise StopIteration
        self.value += 1
        return body
