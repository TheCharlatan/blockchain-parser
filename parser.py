from abc import ABC
from typing import Callable, Optional

from database import Databae


class CoinParser(ABC):
    @abstractmethod
    def parse_blockchain(self, filter: Callable[[bytes, Optional[int]], str], database: Optional[Databae]):
        pass
