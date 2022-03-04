from concurrent.futures import ThreadPoolExecutor
import pickle
import string
import subprocess
import threading
from typing import Callable
import magic
import imghdr
import bitcoin.rpc
import asyncio

import zmq

from database import COIN, Database, DetectorPayload, DetectedDataPayload


def detector_worker(sender: zmq.Socket, detector: Callable[[DetectorPayload], DetectedDataPayload], detector_payload: DetectorPayload):
    detected_data = detector(detector_payload)
    if detected_data.data_length > 1:
        sender.send(pickle.dumps(detected_data))


class DetectorInstance(threading.Thread):
    def __init__(self, receiver: zmq.Socket, sender: zmq.Socket, detector: Callable[[DetectorPayload], DetectedDataPayload]):
        self._receiver = receiver
        self._sender = sender
        self._detector = detector
        threading.Thread.__init__(self)
 
    def run(self):
        executor = ThreadPoolExecutor(100)
        while True:
            detector_payload: DetectedDataPayload = pickle.loads(self._receiver.recv())
            executor.submit(detector_worker, (self._sender, self._detector, detector_payload))


class DetectedDataWriter(threading.Thread):
    def __init__(self, receiver: zmq.Socket, database: Database):
        self._receiver = receiver
        self._database = database
        threading.Thread.__init__(self)

    def run(self):
        while True:
            detected_data_payload: DetectedDataPayload = pickle.loads(self._receiver.recv())
            self._database.insert_detected_ascii_records(detected_data_payload)


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
    process.stdin.write(payload.data)
    output = process.communicate()[0]
    length = len(output.decode("ascii").strip())
    return DetectedDataPayload(payload.txid, payload.data_type, payload.extra_index, length)

#async def gnu_strings_async(detector_payload: DetectorPayload, min: int = 10) -> str:
#    """Find and return a string with the specified minimum size using gnu strings
#    :param bytestring: Bytes to be examined.
#    :type bytestring: bytes
#    :param min: Minimum length of the to be detected string.
#    :type min: int
#    :return: A string of minimum length min as detected in the bytestring.
#    :rtype: str
#    """
#
#    cmd = "strings -n {}".format(min)
#    process = await asyncio.create_subprocess_shell(
#        cmd,
#        stdout=asyncio.subprocess.PIPE,
#        stderr=asyncio.subprocess.STDOUT,
#        stdin=asyncio.subprocess.PIPE,
#    )
#    # process.stdin.write(DetectorPayload.data)
#    output = await process.communicate(input=DetectorPayload.data)[0]
#    return DetectedDataPayload(detector_payload.txid, detector_payload.data_type, detector_payload.extra_index, len(output.decode("ascii").strip()))


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


def native_strings(bytestring: bytes, min: int = 10) -> str:
    """Find and return a string with the specified minimum size using a python native implementation
    :param bytestring: Bytes to be examined.
    :type bytestring: bytes
    :param min: Minimum length of the to be detected string.
    :type min: int
    :return: A string of minimum length min as detected in the bytestring.
    :rtype: str
    """

    for c in bytestring:
        if chr(c) in string.printable:
            result += chr(c)
            continue
        if len(result) >= min:
            return result
        result = ""
    if len(result) >= min:  # catch result at EOF
        return result
    return ""


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
    def __init__(self, coin: COIN, database: Database):
        self._coin = coin
        self._database = database

    def analyze(self):
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
        writer_instance = DetectedDataWriter(database_event_receiver, self._database)
        writer_instance.start()
        self._database.run_detection(detector_event_sender)
