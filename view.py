from typing import Optional
from database import BLOCKCHAIN, Database

# SQL Query for histogram of string lengths:
# SELECT STRING_LENGTH, COUNT(STRING_LENGTH) FROM asciiData GROUP BY STRING_LENGTH ORDER BY STRING_LENGTH

class View:
    def __init__(self, coin: Optional[BLOCKCHAIN], database: Database):
        self._coin = coin
        self._database = database
    
    def view(self) -> None:
        pass