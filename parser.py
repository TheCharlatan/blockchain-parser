from abc import ABC, abstractmethod
from database import BLOCKCHAIN, Database
from pathlib import Path


class DataExtractor(ABC):
    @abstractmethod
    def __init__(self, blockchain_path: Path, coin: BLOCKCHAIN) -> None:
        pass

    @abstractmethod
    def parse_and_extract_blockchain(self, database: Database) -> None:
        pass
