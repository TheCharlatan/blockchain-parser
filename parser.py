from abc import ABC, abstractmethod
from typing import Optional

from database import Database


class CoinParser(ABC):
    @abstractmethod
    def parse_blockchain(self, database: Optional[Database]):
        pass
