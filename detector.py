from concurrent.futures import ThreadPoolExecutor
import string
import subprocess
import threading
from typing import Callable, Optional
import magic
import imghdr
import bitcoin.rpc
from monero.transaction import ExtraParser

import zmq

from database import BLOCKCHAIN, Database, DetectorPayload, DetectedDataPayload


def detector_worker(sender: zmq.Socket, detector: Callable[[DetectorPayload], DetectedDataPayload], detector_payload: DetectorPayload) -> None:
    detected_data = detector(detector_payload)
    if detected_data.data_length > 1:
        sender.send_pyobj(detected_data)


class DetectorInstance(threading.Thread):
    def __init__(self, receiver: zmq.Socket, sender: zmq.Socket, detector: Callable[[DetectorPayload], DetectedDataPayload]):
        self._receiver = receiver
        self._sender = sender
        self._detector = detector
        threading.Thread.__init__(self)
 
    def run(self) -> None:
        executor = ThreadPoolExecutor(10)
        while True:
            detector_payload: DetectorPayload = self._receiver.recv_pyobj()
            # executor.submit(detector_worker, (self._sender, self._detector, detector_payload))
            executor.submit(detector_worker(self._sender, self._detector, detector_payload))


def gnu_strings(payload: DetectorPayload, min: int = 10) -> DetectedDataPayload:
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
    return DetectedDataPayload(payload.txid, payload.data_type, payload.extra_index, length)


def find_file_with_magic(bytestring: bytes) -> str:
    """Find files with the help of magic numbers
    :param bytestring: Bytes to be examined.
    :type bytestring: bytes
    :return: A string with the file type
    :rtype: str
    """

    res = magic.from_buffer(bytestring)
    for op in bytestring:
        if type(op) is int:
            continue
        res = magic.from_buffer(op)
        res = magic.from_buffer(op[1:])
        if res:
            return res

    return ""


def find_file_with_imghdr(bytestring: bytes) -> str:
    """Find images with the help of imghdr magic numbers
    :param bytestring: Bytes to be examined.
    :type bytestring: bytes
    :return: A string with the file type
    :rtype: str
    """

    res = imghdr.what("", bytestring)
    if res:
        return res
    # try again with a potential padding byte removed
    res = imghdr.what("", bytestring[1:])
    if res:
        return res
    return ""


def native_strings(detector_payload: DetectorPayload, min: int = 10) -> DetectedDataPayload:
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
            return DetectedDataPayload(detector_payload.txid, detector_payload.data_type, detector_payload.extra_index, len(result))

        result = ""
    if len(result) >= min:  # catch result at EOF
        return DetectedDataPayload(detector_payload.txid, detector_payload.data_type, detector_payload.extra_index, len(result))
    return DetectedDataPayload(detector_payload.txid, detector_payload.data_type, detector_payload.extra_index, 0)


def monero_find_file_with_magic(detector_payload: DetectorPayload) -> Optional[DetectedDataPayload]:
    import re 
    extra_data = ExtraParser(detector_payload.data)
    probable_data_index = 0
    p = re.compile('offset\s(\d+):*')
    try:
        res = extra_data.parse()
        # filter out entries where the nonces are small
        flag = False
        # filter out transactions without a payment ID
        if "nonces" not in res.keys():
            return None
        for nonce in res["nonces"]:
            if len(nonce) > 9:
                flag = True
        if not flag:
            return None
    # ignore the exceptions, we are only filtering positives anyway
    except ValueError as err:
        match = p.match(str(err))
        if match.group(1) is not None:
            probable_data_index = int(match.group(1))
        res = magic.from_buffer(detector_payload.data[probable_data_index:])

        for i in range(len(detector_payload.data[probable_data_index:])):
            if detector_payload.data[i:i+4] == bytes.fromhex("25504446") or detector_payload.data[i:i+4] == bytes.fromhex("dfbf34eb"):
                print("found PDF!")

        if res == "data" or res == "shared library" or res == "(non-conforming)" or "ARJ" in res or "Applesoft" in res or "GeoSwath" in res or "ISO-8859" in res or "YAC" in res or "capture file" in res or "COFF" in res or "locale data table" in res or "Ucode" in res or "PDP" in res or "LXT" in res or "Tower" in res or "SGI" in res or "BS" in res or "exe" in res or "TeX font" in res or "curses" in res or "endian" in res or "byte" in res or "ASCII" in res:
            return None

        print(res, detector_payload.txid, "offset")
        return DetectedDataPayload("", "", 0, len(res))
    except BaseException:
        pass

    for i in range(len(detector_payload.data[probable_data_index:])):
        if detector_payload.data[i:i+4] == bytes.fromhex("25504446") or detector_payload.data[i:i+4] == bytes.fromhex("dfbf34eb"):
            print("found PDF!")

    res = magic.from_buffer(detector_payload.data)
    if res == "data" or res == "shared library" or res == "(non-conforming)" or "ARJ" in res or "Applesoft" in res or "GeoSwath" in res or "ISO-8859" in res or "YAC" in res or "capture file" in res or "COFF" in res or "locale data table" in res or "Ucode" in res or "PDP" in res or "LXT" in res or "Tower" in res or "SGI" in res or "BS" in res or "exe" in res or "TeX font" in res or "curses" in res or "endian" in res or "byte" in res or "ASCII" in res:
        return None
    print(res, detector_payload.txid, "not offset")



    return DetectedDataPayload("", "", 0, 0)




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


def bitcoin_find_file_with_imghdr(script: bitcoin.core.CScript) -> str:
    """Find images with the help of imghdr magic numbers inside of Bitcoin scripts
        This additional method is defined to allow iteration over different parts of
        a contiguous Bitcoin script.
    :param script: Bitcoin CScript to be examined.
    :type script: bitcoin.core.CScript
    :return: A string with the file type.
    :rtype: str
    """

    # try finding a file in the full script
    res = find_file_with_imghdr(script)
    if res:
        return res
    for op in script:
        # ignore single op codes
        if type(op) is int:
            continue
        # try finding a file in one of the script arguments
        res = find_file_with_imghdr(op)
        if res:
            return res
    return ""


class Detector:
    def __init__(self, coin: BLOCKCHAIN, database: Database):
        self._coin = coin
        self._database = database

    def analyze(self) -> None:
        context = zmq.Context()

        detector_event_sender = context.socket(zmq.PAIR)
        detector_event_receiver = context.socket(zmq.PAIR)
        detector_event_sender.bind("inproc://detector_bridge")
        detector_event_receiver.connect("inproc://detector_bridge")

        database_event_sender = context.socket(zmq.PAIR)
        database_event_receiver = context.socket(zmq.PAIR)
        database_event_sender.bind("inproc://database_bridge")
        database_event_receiver.connect("inproc://database_bridge")

        detector_instance = DetectorInstance(detector_event_receiver, database_event_sender, gnu_strings)
        detector_instance.start()
        # writer_instance = DetectedDataWriter(database_event_receiver, self._database)
        # writer_instance.start()
        # self._database.run_detection(detector_event_sender, database_event_receiver)
        self._database.run_detection(monero_find_file_with_magic)
