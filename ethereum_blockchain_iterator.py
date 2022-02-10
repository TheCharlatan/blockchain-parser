from ethereum_freezer_tables import FreezerBodiesTable, FreezerHeadersTable


class ParseEthereumBlockHeaders:
    def __init__(self, ancient_chaindata_path: str):
        self.table = FreezerHeadersTable(ancient_chaindata_path)
        self.value = 0
        self.header = self.table.get_header_by_height(self.value)
    
    def __iter__(self):
        return self
    
    def __next__(self):
        try:
            header = self.table.get_header_by_height(self.value + 1)
        except:
            raise StopIteration
        self.value += 1
        return header

class ParseEthereumBlockBodies:
    def __init__(self, ancient_chaindata_path: str):
        self.table = FreezerBodiesTable(ancient_chaindata_path)
        self.value = 0
        self.header = self.table.get_body_by_height(self.value)
    
    def __iter__(self):
        return self

    def __next__(self):
        try:
            body = self.table.get_body_by_height(self.value + 1)
        except:
            raise StopIteration
        self.value += 1
        return body

    
