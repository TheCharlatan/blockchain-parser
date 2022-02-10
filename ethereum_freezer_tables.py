from typing import Dict, List, Tuple
import io
import snappy
import os
import rlp

from ethereum_rlp import Body, Header

freezerHeadersTable = "headers"
freezerHashesTable = "hashes"
freezerBodiesTable = "bodies"
freezerReceiptsTable = "receipts"
freezerDifficultiesTable = "diffs"

freezerTableSize = 2 * 1000 * 1000 * 1000
indexEntrySize = 6

class IndexEntry:
    """
        filenum: 2 byte integer
        offset: 4 byte integer
    """

    __slots__ = ("filenum", "offset")

    def __init__(self, b: bytes):
        """ Deserializes binary b into a rawIndex object.  """
        self.filenum = int.from_bytes(b[:2], "big")
        self.offset = int.from_bytes(b[2:6], "big")

    def append(self, b: bytes) -> bytes:
        """ Append indexEntry to bytes """
        offset = len(b)
        return b + self.filenum.to_bytes(2, "big") + self.offset.to_bytes(4, "big")
    
    def __repr__(self):
        return f"IndexEntry(filenum={self.filenum} offset={self.offset})"


def bounds(start: IndexEntry, end: IndexEntry) -> bytes:
    """ Bounds returns the start and end offsets and the file number of where to read 
        the data item marked by the two index entries. The two entries are assumed to be sequential
    """
    if start.filenum != end.filenum:
        # If a piece of data 'crosses' a data-file,
        # it's actually in one piece on the second data-file.
        # We return a zero-indexEntry for the second file as start
        return 0, end.offset, end.filenum
    return start.offset, end.offset, end.filenum


class FreezerTable:
    items: int = 0  # number of items stored in the table

    noCompression: bool
    readonly: bool
    maxFileSize: int = 100 * 1000 * 1000 * 1000
    name: str
    path: str

    head: str = ""  # File descriptor for the data head of the table
    files: Dict[int, str]  # open files
    headId: int = 0  # number of the currently active head file
    tailId: int = 0  # number of the earliest file
    index: str  # file descriptor for the index entry file of the table

    itemOffset: int = 0  # Offset (number of discarded items)

    headBytes: int = 0

    def __init__(self, path: str, name: str, disableSnappy: bool, readonly: bool):
        noCompression = disableSnappy
        if not os.path.isdir(path):
            raise Exception(f"path not found {path}")

        idxName: str
        if noCompression:
            idxName = f"{name}.ridx"
        else:
            idxName = f"{name}.cidx"

        offsets: io.TextIOWrapper
        if readonly:
            offsets = path + "/" + idxName

        self.files = {}
        self.index = offsets
        self.name = name
        self.path = path
        self.noCompression = noCompression
        self.readonly = readonly
        self.repair()

    def repair(self):
        buffer: bytes
        # Ensure the index i s a multiple of indexEntrySize bytes
        if os.stat(self.index).st_size % indexEntrySize:
            raise Exception(
                f"index is not a multiple of indexEntry Size {indexEntrySize}"
            )

        # Get the file index size
        offsetsSize = os.stat(self.index).st_size

        # Read the index zero to determine which file is the earliest and what item offset to use
        buffer: bytes
        with open(self.index, 'rb') as f:
            buffer = f.read(indexEntrySize)
            print(buffer)
        firstIndex = IndexEntry(buffer)
        print("first Index:", firstIndex)
        self.tailId = firstIndex.filenum
        self.itemOffset = firstIndex.offset

        with open(self.index, 'rb') as f:
            f.seek(offsetsSize - indexEntrySize)
            buffer = f.read(indexEntrySize)
            print(buffer)
        
        lastIndex = IndexEntry(buffer)
        print("last Index:", lastIndex)
        self.head = self.openFile(lastIndex.filenum)
        contentSize = os.stat(self.head).st_size
        if contentSize is None:
            raise Exception("file could not be statted")
        
        self.headBytes = contentSize
        self.items = self.itemOffset + int(offsetsSize/indexEntrySize-1)
        self.headId = lastIndex.filenum

    def openFile(self, num: int) -> str:
        """ Doesn't actually open a file, but constructs the correct filename and fills the table 
            TODO: change the function name once we are done with the code port 
        """
        if num not in self.files:
            name: str
            if self.noCompression:
                name = self.path + "/" + f"{self.name}.%04d.rdat" % num
            else:
                name = self.path + "/" + f"{self.name}.%04d.cdat" % num
            self.files[num] = name
        return self.files[num]

    def Retrieve(self, item: int) -> bytes:
        items = self.RetrieveItems(item, 1, 0)
        return items[0]
    
    def RetrieveItems(self, start: int, count: int, maxBytes: int) -> List[bytes]:
        diskData, sizes = self.retrieveItems(start, count, maxBytes)
        print("diskData:", diskData)
        output = []
        offset = 0 # offset for reading
        outputSize = 0 # size of uncompressed data

        # Slice up the data and decompress
        for (i, diskSize) in enumerate(sizes):
            item = diskData[offset: offset+diskSize]
            offset += diskSize
            decompressedSize = diskSize
            data: bytes
            # check the length first
            if not self.noCompression:
                print(item)
                data = snappy.decompress(item)
                decompressedSize = len(data)
                # decompressedSize = snappy.DecodeLen(item)
            if i > 0 and (outputSize+decompressedSize) > maxBytes:
                break
            if not self.noCompression:
                output.append(data)
            else:
                output.append(item)
            outputSize += decompressedSize
        
        return output
            
    
    def retrieveItems(self, start: int, count: int, maxBytes: int) -> Tuple[bytes, List[int]]:
        """" Reads up to 'count' items from the table. Reads at least one itme, but otherwise avoids 
        reading more than maxBytes bytes. Return the (potentially compressed) data, and the sizes 
        """

        # Ensure the table is initialized
        if self.index is None or self.head is None:
            raise Exception("table not open")
        
        itemCount = self.items
        # Ensure the start is written, not deleted from the tail, and that the
        # caller actually wants something
        if itemCount <= start or self.itemOffset > start or count == 0:
            raise Exception("item out of bounds")
        if start+count > itemCount:
            count = itemCount - start

        output: bytearray = bytearray(b'')
        outputSize = 0
        
        def readData(fileId: int, start: int, length: int, output: bytearray):
            dataFile = self.files[fileId]
            if dataFile is None:
                raise Exception("missing data file %d", fileId)
            with open(dataFile, 'rb') as f:
                f.seek(start)
                output.extend(f.read(length))

        indices = self.getIndices(start, count)
        print("indices:", indices)

        sizes = []
        totalSize = 0
        readStart = indices[0].offset
        unreadSize = 0

        for (i, firstIndex) in enumerate(indices[:-1]):
            secondIndex = indices[i+1]
            # Determine the size of the item
            (offset1, offset2, _) = bounds(firstIndex, secondIndex)
            size = int(offset2 - offset1)
            # Crossing a file boundary?
            if secondIndex.filenum != firstIndex.filenum:
                # If we have unread data in the first file, we need to do that read now
                if unreadSize > 0:
                    readData(firstIndex.filenum, readStart, unreadSize, output)
                    outputSize += unreadSize
                    unreadSize = 0
                    readStart = 0
            if i>0 and (totalSize+size) > maxBytes:
                # About to break out due ot byte limit being exceeded. We don't 
                # read this last item, but we need to do the deferred reads now.
                if unreadSize > 0:
                    readData(secondIndex.filenum, readStart, unreadSize, output)
                    outputSize += unreadSize
                break

            # Defer the read for later
            unreadSize += size
            totalSize += size
            sizes.append(size)
            if i == len(indices)-2 or totalSize > maxBytes:
                readData(secondIndex.filenum, readStart, unreadSize, output)
                outputSize += unreadSize
        print("retrieved data:", output)
        print("output size:", outputSize)
        print("data to be returned:", output[:outputSize])

        return (bytes(output[:outputSize]), sizes)


    def getIndices(self, _from: int, count: int) -> List[IndexEntry]:
        """ Returns the index entries for the given from-item, covering 'count' items.
        N.B.: The actual number of returned indices for N items will always be N+1 (unless
        an error is returned).
        OBS: This method assumes that the caller has already verified (and/or trimmed) the
        range so that the items are within bounds. If this method is used to read out of bounds, 
        it will raise an exception.
        """
        print("from: ", _from)
        # Apply the table-offset
        _from = _from - self.itemOffset
        print("from offset: ", _from)
        # For reading N items, we need N+1 indices
        buffer: bytes
        with open(self.index, 'rb') as f:
            f.seek(_from*indexEntrySize)
            buffer = f.read((count+1)*indexEntrySize)

        offset = 0
        indices = []
        for _ in range(_from, _from+count+1):
            index = IndexEntry(buffer[offset:])
            offset += indexEntrySize
            indices.append(index)
        
        if _from == 0:
            # Special case if we're reading the first item in the freezer. We assume that the
            # First item always starts from zero. This means we can use the first item metadata
            # to carry information about the 'global' offset, for the delection-case
            indices[0].offset = 0
            indices[0].filenum = indices[1].filenum
        
        return indices


class FreezerHashesTable(FreezerTable):
    def __init__(self, ancient_chaindata_path: str):
        super(FreezerHashesTable, self).__init__(ancient_chaindata_path, freezerHashesTable, True, True)
    
    def get_hash_by_height(self, height: int) -> bytes:
        return self.Retrieve(height)
    
class FreezerBodiesTable(FreezerTable):
    def __init__(self, ancient_chaindata_path: str):
        super(FreezerBodiesTable, self).__init__(ancient_chaindata_path, freezerBodiesTable, False, True)
    
    def get_body_by_height(self, height: int) -> Body:
        return rlp.decode(self.Retrieve(height), Body)

class FreezerHeadersTable(FreezerTable):
    def __init__(self, ancient_chaindata_path: str):
        super(FreezerHeadersTable, self).__init__(ancient_chaindata_path, freezerHeadersTable, False, True)

    def get_header_by_height(self, height: int) -> Header:
        return rlp.decode(self.Retrieve(height), Header)
