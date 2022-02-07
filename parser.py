from abc import ABC, abstractmethod
from typing import Callable, Optional

from database import Database


class CoinParser(ABC):
    @abstractmethod
    def parse_blockchain(self, database: Optional[Database]):
        pass
