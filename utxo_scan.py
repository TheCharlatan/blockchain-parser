# This is a slightly modified version of
# https://github.com/sr-gi/bitcoin_tools/blob/0f6ea45b6368200e481982982822f0416e0c438d/bitcoin_tools/analysis/status/utils.py#L843
# ported to python3

from pathlib import Path
import plyvel
from binascii import hexlify, unhexlify
from typing import Any, Callable, Dict, Optional
from database import BLOCKCHAIN, DATATYPE, Database


NSPECIALSCRIPTS = 6

# source: https://github.com/bitcoin/bitcoin/blob/v0.13.2/src/compressor.cpp#L98
# man, this is disappointing, to say the least, it's so inefficient!
out_type = {
    0: "p2pkh",
    1: "p2sh",
    2: "p2pk",
    3: "p2pk",
    4: "p2pk",
    5: "p2pk",
}


def txout_decompress(x):
    """Decompresses the Satoshi amount of a UTXO stored in the LevelDB. Code is a port from the Bitcoin Core C++
    source:
        https://github.com/bitcoin/bitcoin/blob/v0.13.2/src/compressor.cpp#L161#L185
    :param x: Compressed amount to be decompressed.
    :type x: int
    :return: The decompressed amount of satoshi.
    :rtype: int
    """

    if x == 0:
        return 0
    x -= 1
    e = x % 10
    x /= 10
    if e < 9:
        d = (x % 9) + 1
        x /= 9
        n = x * 10 + d
    else:
        n = x + 1
    while e > 0:
        n *= 10
        e -= 1
    return n


def b128_decode(data):
    """Performs the MSB base-128 decoding of a given value. Used to decode variable integers (varints) from the LevelDB.
    The code is a port from the Bitcoin Core C++ source. Notice that the code is not exactly the same since the original
    one reads directly from the LevelDB.
    The decoding is used to decode Satoshi amounts stored in the Bitcoin LevelDB (chainstate). After decoding, values
    are decompressed using txout_decompress.
    The decoding can be also used to decode block height values stored in the LevelDB. In his case, values are not
    compressed.
    Original code can be found in:
        https://github.com/bitcoin/bitcoin/blob/v0.13.2/src/serialize.h#L360#L372
    Examples and further explanation can be found in b128_encode function.
    :param data: The base-128 encoded value to be decoded.
    :type data: hex str
    :return: The decoded value
    :rtype: int
    """

    n = 0
    i = 0
    while True:
        d = int(data[2 * i: 2 * i + 2], 16)
        n = n << 7 | d & 0x7F
        if d & 0x80:
            n += 1
            i += 1
        else:
            return n


def parse_b128(utxo, offset=0):
    """Parses a given serialized UTXO to extract a base-128 varint.
    :param utxo: Serialized UTXO from which the varint will be parsed.
    :type utxo: hex str
    :param offset: Offset where the beginning of the varint if located in the UTXO.
    :type offset: int
    :return: The extracted varint, and the offset of the byte located right after it.
    :rtype: hex str, int
    """

    data = utxo[offset: offset + 2]
    offset += 2
    more_bytes = (
        int(data, 16) & 0x80
    )  # MSB b128 Varints have set the bit 128 for every byte but the last one,
    # indicating that there is an additional byte following the one being analyzed. If bit 128 of the byte being read is
    # not set, we are analyzing the last byte, otherwise, we should continue reading.
    while more_bytes:
        data += utxo[offset: offset + 2]
        more_bytes = int(utxo[offset: offset + 2], 16) & 0x80
        offset += 2

    return data, offset


def decode_utxo(coin, outpoint):
    """
    Decodes a LevelDB serialized UTXO for Bitcoin core v 0.15 onwards. The serialized format is defined in the Bitcoin
    Core source code as outpoint:coin.
    Outpoint structure is as follows: key | tx_hash | index.
    Where the key corresponds to b'C', or 43 in hex. The transaction hash in encoded in Little endian, and the index
    is a base128 varint. The corresponding Bitcoin Core source code can be found at:
    https://github.com/bitcoin/bitcoin/blob/ea729d55b4dbd17a53ced474a8457d4759cfb5a5/src/txdb.cpp#L40-L53
    On the other hand, a coin if formed by: code | value | out_type | script.
    Where code encodes the block height and whether the tx is coinbase or not, as 2*height + coinbase, the value is
    a txout_compressed base128 Varint, the out_type is also a base128 Varint, and the script is the remaining data.
    The corresponding Bitcoin Core soruce code can be found at:
    https://github.com/bitcoin/bitcoin/blob/6c4fecfaf7beefad0d1c3f8520bf50bb515a0716/src/coins.h#L58-L64
    :param coin: The coin to be decoded (extracted from the chainstate)
    :type coin: str
    :param outpoint: The outpoint to be decoded (extracted from the chainstate)
    :type outpoint: str
    :return; The decoded UTXO.
    :rtype: dict
    """

    # First we will parse all the data encoded in the outpoint, that is, the transaction id and index of the utxo.
    # Check that the input data corresponds to a transaction.
    assert outpoint[:2] == b"43"
    # Check the provided outpoint has at least the minimum length (1 byte of key code, 32 bytes tx id, 1 byte index)
    assert len(outpoint) >= 68
    # Get the transaction id (LE) by parsing the next 32 bytes of the outpoint.
    tx_id = outpoint[2:66]
    # Finally get the transaction index by decoding the remaining bytes as a b128 VARINT
    tx_index = b128_decode(outpoint[66:])

    # Once all the outpoint data has been parsed, we can proceed with the data encoded in the coin, that is, block
    # height, whether the transaction is coinbase or not, value, script type and script.
    # We start by decoding the first b128 VARINT of the provided data, that may contain 2*Height + coinbase
    code, offset = parse_b128(coin)
    code = b128_decode(code)
    height = code >> 1
    coinbase = code & 0x01

    # The next value in the sequence corresponds to the utxo value, the amount of Satoshi hold by the utxo. Data is
    # encoded as a B128 VARINT, and compressed using the equivalent to txout_compressor.
    data, offset = parse_b128(coin, offset)
    amount = txout_decompress(b128_decode(data))

    # Finally, we can obtain the data type by parsing the last B128 VARINT
    out_type, offset = parse_b128(coin, offset)
    out_type = b128_decode(out_type)

    if out_type in [0, 1]:
        data_size = 40  # 20 bytes
    elif out_type in [2, 3, 4, 5]:
        data_size = 66  # 33 bytes (1 byte for the type + 32 bytes of data)
        offset -= 2
    # Finally, if another value is found, it represents the length of the following data, which is uncompressed.
    else:
        data_size = (
            out_type - NSPECIALSCRIPTS
        ) * 2  # If the data is not compacted, the out_type corresponds
        # to the data size adding the number os special scripts (nSpecialScripts).

    # And the remaining data corresponds to the script.
    script = coin[offset:]

    # Assert that the script hash the expected length
    assert len(script) == data_size

    # And to conclude, the output can be encoded. We will store it in a list for backward compatibility with the
    # previous decoder
    out = {"amount": amount, "out_type": out_type, "data": script}

    # Even though there is just one output, we will identify it as outputs for backward compatibility with the previous
    # decoder.
    return {
        "tx_id": tx_id,
        "index": tx_index,
        "coinbase": coinbase,
        "out": out,
        "height": height,
    }


def deobfuscate_value(obfuscation_key, value):
    """
    De-obfuscate a given value parsed from the chainstate.
    :param obfuscation_key: Key used to obfuscate the given value (extracted from the chainstate).
    :type obfuscation_key: str
    :param value: Obfuscated value.
    :type value: str
    :return: The de-obfuscated value.
    :rtype: str.
    """

    l_value = len(value)
    l_obf = len(obfuscation_key)

    # Get the extended obfuscation key by concatenating the obfuscation key with itself until it is as large as the
    # value to be de-obfuscated.
    if l_obf < l_value:
        extended_key = (obfuscation_key * int((l_value / l_obf) + 1))[:l_value]
    else:
        extended_key = obfuscation_key[:l_value]

    r = format(int(value, 16) ^ int(extended_key, 16), "x").zfill(l_value)

    return r


def parse_ldb(
    database: Optional[Database],
    coin=BLOCKCHAIN.BITCOIN_MAINNET,
    btc_dir="/home/drgrid/.bitcoin",
    fin_name="chainstate",
):
    """
    Parsed data from the chainstate LevelDB and stores it in a output file.
    :param btc_dir: Path of the bitcoin data directory
    :type btc_dir: str
    :param fin_name: Name of the LevelDB folder (chainstate by default)
    :type fin_name: str
    :return: None
    :rtype: None
    """

    # The UTXOs in the database are prefixed with a 'C'
    prefix = b"C"
    # Open the LevelDB
    db = plyvel.DB(
        btc_dir + "/" + fin_name, compression=None
    )  # Change with path to chainstate

    # Load obfuscation key (if it exists)
    o_key = db.get((unhexlify("0e00") + b"obfuscate_key"))

    # If the key exists, the leading byte indicates the length of the key (8 byte by default). If there is no key,
    # 8-byte zeros are used (since the key will be XORed with the given values).
    if o_key is not None:
        o_key = hexlify(o_key)[2:]

    # For every UTXO (identified with a leading 'c'), the key (tx_id) and the value (encoded utxo) is displayed.
    # UTXOs are obfuscated using the obfuscation key (o_key), in order to get them non-obfuscated, a XOR between the
    # value and the key (concatenated until the length of the value is reached) if performed).
    count = 0
    for key, o_value in db.iterator(prefix=prefix):
        serialized_length = len(key) + len(o_value)
        key = hexlify(key)
        if o_key is not None:
            value = deobfuscate_value(o_key, hexlify(o_value))
        else:
            value = hexlify(o_value)

        value = decode_utxo(value, key)
        count += 1
        if count % 10000 == 0:
            print(count, value)

        if database is not None:
            database.insert_record(
                value.out.data,
                value.tx_id,
                coin,
                DATATYPE.SCRIPT_PUBKEY,
                value.height,
                value.index,
            )

    db.close()


class UTXOIterator:
    def __init__(
        self,
        path: Path=Path("/home/drgrid/.bitcoin"),
        fin_name: str="chainstate",
    ) -> None:
        """
        Parsed data from the chainstate LevelDB and stores it in a output file.
        :param btc_dir: Path of the bitcoin data directory
        :type btc_dir: str
        :param fin_name: Name of the LevelDB folder (chainstate by default)
        :type fin_name: str
        :return: None
        :rtype: None
        """

        # The UTXOs in the database are prefixed with a 'C'
        prefix = b"C"
        # Open the LevelDB
        db = plyvel.DB(
            str(path.expanduser()) + "/" + fin_name, compression=None
        )  # Change with path to chainstate

        # Load obfuscation key (if it exists)
        o_key = db.get((unhexlify("0e00") + b"obfuscate_key"))

        # If the key exists, the leading byte indicates the length of the key (8 byte by default). If there is no key,
        # 8-byte zeros are used (since the key will be XORed with the given values).
        if o_key is not None:
            o_key = hexlify(o_key)[2:]

        # For every UTXO (identified with a leading 'c'), the key (tx_id) and the value (encoded utxo) is displayed.
        # UTXOs are obfuscated using the obfuscation key (o_key), in order to get them non-obfuscated, a XOR between the
        # value and the key (concatenated until the length of the value is reached) if performed).

        self._o_key = o_key
        self._prefix = prefix
        self._iterator = db.iterator(prefix=prefix)

    def __iter__(self) -> Dict[str, Any]:
        key, o_value = self._iterator.__next__()
        key = hexlify(key)
        if self._o_key is not None:
            value = deobfuscate_value(self._o_key, hexlify(o_value))
        else:
            value = hexlify(o_value)

        return decode_utxo(value, key)
