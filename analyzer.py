from concurrent.futures import ThreadPoolExecutor
import enum
import sqlite3
import string
import subprocess
import threading
from typing import Any, Callable, Iterable, Optional
import magic
import imghdr
import bitcoin.rpc
from monero.transaction import ExtraParser
import re

import zmq

from database import BLOCKCHAIN, Database, DetectedAsciiPayload, DetectedFilePayload, DetectorFunc, DetectorPayload


def analysis_worker(sender: zmq.Socket, detector: DetectorFunc, detector_payload: DetectorPayload) -> None:
    detected_data = detector(detector_payload)
    if detected_data is None:
        return
    sender.send_pyobj(detected_data)


class AnalyzerInstance(threading.Thread):
    def __init__(self, receiver: zmq.Socket, sender: zmq.Socket, detector: DetectorFunc):
        self._receiver = receiver
        self._sender = sender
        self._detector = detector
        threading.Thread.__init__(self)
 
    def run(self) -> None:
        executor = ThreadPoolExecutor(10)
        while True:
            detector_payload: DetectorPayload = self._receiver.recv_pyobj()
            # executor.submit(detector_worker, (self._sender, self._detector, detector_payload))
            executor.submit(analysis_worker(self._sender, self._detector, detector_payload))


def gnu_strings(payload: DetectorPayload, min: int = 10) -> Optional[DetectedAsciiPayload]:
    """Find and return a string with the specified minimum size using gnu strings
    :param bytestring: Bytes to be examined.
    :type bytestring: bytes
    :param min: Minimum length of the to be detected string.
    :type min: int
    :return: A string of minimum length min as detected in the bytestring.
    :rtype: str
    """

    cmd = "strings -n {}".format(min)
    process = subprocess.Popen(
        cmd,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        stdin=subprocess.PIPE,
    )
    assert process.stdin is not None
    process.stdin.write(payload.data)
    output = process.communicate()[0]
    print(output)
    length = len(output.decode("ascii").strip())
    print(output.decode("ascii").strip())
    if length >= min:
        return DetectedAsciiPayload(payload.txid, payload.data_type, payload.extra_index, length)
    return None


def bitcoin_detect_op_return_output(script: bitcoin.core.script.CScript) -> str:
    """Return true if the script contains the OP_RETURN opcode
    :param script: Bitcoin CScript to be examined.
    :type script: bitcoin.core.script.CScript
    :return: 'OP_RETURN' if the output script is indeed OP_RETURN, '' if not
    :rtype: str
    """

    for elem in script.raw_iter():
        for code in elem:
            if code == bitcoin.core.script.OP_RETURN:
                return "OP_RETURN"
    return ""


def native_strings(detector_payload: DetectorPayload, min: int = 10) -> Optional[DetectedAsciiPayload]:
    """Find and return a string with the specified minimum size using a python native implementation
    :param bytestring: Bytes to be examined.
    :type bytestring: bytes
    :param min: Minimum length of the to be detected string.
    :type min: int
    :return: A string of minimum length min as detected in the bytestring.
    :rtype: str
    """

    result = ""
    for c in detector_payload.data:
        if chr(c) in string.printable:
            result += chr(c)
            continue
        if len(result) >= min:
            return DetectedAsciiPayload(detector_payload.txid, detector_payload.data_type, detector_payload.extra_index, len(result))

        result = ""
    if len(result) >= min:  # catch result at EOF
        return DetectedAsciiPayload(detector_payload.txid, detector_payload.data_type, detector_payload.extra_index, len(result))
    return None


def find_file_with_imghdr(data: bytes) -> Optional[str]:
    """Find images with the help of imghdr magic numbers
    :param bytestring: Bytes to be examined.
    :type bytestring: bytes
    :return: A string with the file type
    :rtype: str
    """

    res = imghdr.what("", data)
    if res:
        return res
    # try again with a potential padding byte removed
    res = imghdr.what("", data[1:])
    return res

def find_file_with_magic(data: bytes) -> Optional[str]:
    """Find files with the help of magic numbers library"""
    if len(data) < 8:
        return None
    res = magic.from_buffer(data)
    # try again with a potential padding byte removed
    if res == "data":
        res = magic.from_buffer(data[1:])
    if res == "data" or res == "shared library" or res == "(non-conforming)" or "ctors/track" in res or "ICE authority" in res or "SAS" in res or "Stereo" in res or "ddis/dtif" in res or "Virtual TI skin" in res or "Multitracker" in res or "HP s200" in res or "ECMA-363" in res or "Monaural" in res or "32 kHz" in res or "48 kHz" in res or "locale archive" in res or "terminfo" in res or "GRand" in res or "font" in res or "Apache" in res or "OEM-ID" in res or "Bentley" in res or "huf output" in res or "disk quotas" in res or "PRCS" in res or "PEX" in res or "C64" in res or "lif file" in res or "GHost image" in res or "Linux" in res or "amd" in res or "XENIX" in res or "structured file" in res or "gfxboot" in res or "X11" in res or "cpio" in res or "Squeezed" in res or "compacted" in res or "Quasijarus" in res or "JVT" in res or "Poskanzer" in res or "VISX" in res or "TIM" in res or "PCX" in res or "MSVC" in res or "LZH" in res or "LVM1" in res or "Encore" in res or "ATSC" in res or "BASIC" in res or "frozen file" in res or "dBase" in res or "SCO" in res or "RDI" in res or "PostScript" in res or "Netpbm" in res or "Maple" in res or "i386" in res or "archive data" in res or "Motorola" in res or "FoxPro" in res or "packed data" in res or "fsav" in res or "crunched" in res or "compress'd" in res or "Terse" in res or "SoftQuad" in res or "Sendmail" in res or "OS9" in res or "MySQL" in res or "IRIS" in res or "Java" in res or "SOFF" in res or "PSI " in res or "Clarion" in res or "BIOS" in res or "Atari" in res or "Ai32" in res or "ALAN" in res or "44.1" in res or "Microsoft" in res or "TeX" in res or "floppy" in res or "GLF_BINARY" in res or "AIN" in res or "Alpha" in res or "vfont" in res or "DOS" in res or "Sun disk" in res or "Group 3" in res or "Logitech" in res or "Solitaire" in res or "old " in res or "SYMMETRY" in res or "DOS/MBR" in res or "Amiga" in res or "mumps" in res or "ID tags" in res or "GLS" in res or "dBase IV DBT" in res or "TTComp" in res or "EBCDIC" in res or "MGR bitmap" in res or "CLIPPER" in res or "Dyalog" in res or "PARIX" in res or "AIX" in res or "SysEx" in res or "ARJ" in res or "Applesoft" in res or "GeoSwath" in res or "ISO-8859" in res or "YAC" in res or "capture file" in res or "COFF" in res or "locale data table" in res or "Ucode" in res or "PDP" in res or "LXT" in res or "Tower" in res or "SGI" in res or "BS" in res or "exe" in res or "curses" in res or "endian" in res or "byte" in res or "ASCII" in res:
        return None
    if "MPEG" in res:
        return "MPEG stream"
    if "gzip compressed data" in res:
        return "gzip compressed data"
    if "PGP Secret" in res or 'PGP\\011Secret' in res:
        return "PGP Secret key"
    if "PGP symmetric" in res:
        return "PGP symmetric key encrypted data"
    if "Bio-Rad" in res:
        return "Bio-Rad .PIC Image File"
    if "Targa" in res:
        return "Targa image data"
    return res

def get_monero_offset_regex() -> re.Pattern:
    return re.compile('offset\s(\d+):*')

def monero_find_file_within_extra(detector_payload: DetectorPayload, file_detector_func: Callable[[bytes], Optional[str]]) -> Optional[DetectedFilePayload]:
    extra_data = ExtraParser(detector_payload.data)
    probable_data_index = 0
    try: 
        parsed_extra = extra_data.parse()
        # check every first and second byte in the nonces
        if "nonces" in parsed_extra.keys():
            for nonce in parsed_extra["nonces"]:
                res = file_detector_func(nonce)
                if res is not None:
                    return DetectedFilePayload(detector_payload.txid, detector_payload.data_type, detector_payload.extra_index, res)
        
        # check every first and second byte in the pubkey
        if "pubkeys" in parsed_extra.keys():
            for pubkey in parsed_extra["pubkeys"]:
                find_file_with_imghdr(pubkey)
                if res is not None:
                    return DetectedFilePayload(detector_payload.txid, detector_payload.data_type, detector_payload.extra_index, res)

    except ValueError as err:
        # get the offset of the non-standard tx extra data
        match = get_monero_offset_regex().match(str(err))
        if match is None:
            pass
        else:
            if match.group(1) is not None:
                probable_data_index = int(match.group(1))
            res = file_detector_func(detector_payload.data[probable_data_index:])
            if res is not None:
                return DetectedFilePayload(detector_payload.txid, detector_payload.data_type, detector_payload.extra_index, res)

    except BaseException:
        pass

    res = file_detector_func(detector_payload.data)
    if res is not None:
        return DetectedFilePayload(detector_payload.txid, detector_payload.data_type, detector_payload.extra_index, res)
    return None

def monero_find_file_with_magic(detector_payload: DetectorPayload) -> Optional[DetectedFilePayload]:
    return monero_find_file_within_extra(detector_payload, find_file_with_magic)

def monero_find_file_with_imghdr(detector_payload: DetectorPayload) -> Optional[DetectedFilePayload]:
    return monero_find_file_within_extra(detector_payload, find_file_with_imghdr)

def bitcoin_find_file_within_script(detector_payload: DetectorPayload, file_detector_func: Callable[[bytes], Optional[str]]) -> Optional[DetectedFilePayload]:
    script = bitcoin.rpc.bitcoin.bitcoin.core.CScript(detector_payload.data)
    # try finding a file in the full script
    res = file_detector_func(script)
    if res is not None:
        return DetectedFilePayload(detector_payload.txid, detector_payload.data_type, detector_payload.extra_index, res)

    try:
        for op in script:
            # ignore single op codes
            if type(op) is int:
                continue
            # try finding a file in one of the script arguments
            if type(op) is bitcoin.rpc.bitcoin.bitcoin.core.script.CScriptOp:
                continue
            res = file_detector_func(op)
            if res is not None:
                return DetectedFilePayload(detector_payload.txid, detector_payload.data_type, detector_payload.extra_index, res)
    except:
        res = file_detector_func(script)
        if res is not None:
            return DetectedFilePayload(detector_payload.txid, detector_payload.data_type, detector_payload.extra_index, res)
        pass

    return None

def bitcoin_find_file_with_magic(detector_payload: DetectorPayload) -> Optional[DetectedFilePayload]:
    return bitcoin_find_file_within_script(detector_payload, find_file_with_magic)

def bitcoin_find_file_with_imghdr(detector_payload: DetectorPayload) -> Optional[DetectedFilePayload]:
    return bitcoin_find_file_within_script(detector_payload, find_file_with_imghdr)

def ethereum_find_file_within_data(detector_payload: DetectorPayload, file_detector_func: Callable[[bytes], Optional[str]]) -> Optional[DetectedFilePayload]:
    res = file_detector_func(detector_payload.data)
    if res is not None:
        return DetectedFilePayload(detector_payload.txid, detector_payload.data_type, detector_payload.extra_index, res)
    return None

def ethereum_find_file_with_magic(detector_payload: DetectorPayload) -> Optional[DetectedFilePayload]:
    return ethereum_find_file_within_data(detector_payload, find_file_with_magic)

def ethereum_find_file_with_imghdr(detector_payload: DetectorPayload) -> Optional[DetectedFilePayload]:
    return ethereum_find_file_within_data(detector_payload, find_file_with_imghdr)


class Detector(enum.Enum):
    native_strings = "native_strings"
    gnu_strings = "gnu_strings"
    imghdr_files = "imghdr_files"
    magic_files = "magic_files"


class Analyzer:
    def __init__(self, blockchain: Optional[BLOCKCHAIN], database: Database):
        self._blockchain = blockchain
        self._database = database

    def analyze(self, detector: Detector) -> None:
        context = zmq.Context()

        detector_func: DetectorFunc 
        database_write_func: Callable[[Iterable[Any], sqlite3.Connection], None]
        if detector == Detector.native_strings:
            detector_func = native_strings
            database_write_func = self._database.insert_detected_ascii_records
        elif detector == Detector.gnu_strings:
            detector_func = gnu_strings
            database_write_func = self._database.insert_detected_ascii_records
        elif detector == Detector.magic_files:
            database_write_func = self._database.insert_detected_magic_file_records
            if self._blockchain is not None:
                if "monero" in self._blockchain.value:
                    detector_func = monero_find_file_with_magic
                elif "bitcoin" in self._blockchain.value:
                    detector_func = bitcoin_find_file_with_magic
                elif "ethereum" in self._blockchain.value:
                    detector_func = ethereum_find_file_with_magic
                else:
                    raise BaseException("no detector implementation for this blockchain / detector tuple")
            else:
                raise BaseException("no detector implementation for this blockchain / detector tuple")
        elif detector == Detector.imghdr_files:
            database_write_func = self._database.insert_detected_imghdr_file_records
            if self._blockchain is not None:
                if "monero" in self._blockchain.value:
                    detector_func = monero_find_file_with_imghdr
                elif "bitcoin" in self._blockchain.value:
                    detector_func = bitcoin_find_file_with_imghdr
                elif "ethereum" in self._blockchain.value:
                    detector_func = ethereum_find_file_with_imghdr
                else:
                    raise BaseException("no detector implementation for this blockchain / detector tuple")
            else:
                raise BaseException("no detector implementation for this blockchain / detector tuple")


        detector_event_sender = context.socket(zmq.PAIR)
        detector_event_receiver = context.socket(zmq.PAIR)
        detector_event_sender.bind("inproc://detector_bridge")
        detector_event_receiver.connect("inproc://detector_bridge")

        database_event_sender = context.socket(zmq.PAIR)
        database_event_receiver = context.socket(zmq.PAIR)
        database_event_sender.bind("inproc://database_bridge")
        database_event_receiver.connect("inproc://database_bridge")

        self._database.run_detection(detector_func, database_write_func, self._blockchain)
