from abc import ABC, abstractmethod
from typing import Callable, Optional

from database import Database


class CoinParser(ABC):
    @abstractmethod
    def parse_blockchain(self, filter: Callable[[bytes, Optional[int]], str], database: Optional[Database]):
        pass
