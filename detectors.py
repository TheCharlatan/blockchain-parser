import string
import subprocess
import magic
import imghdr
import bitcoin.rpc


def gnu_strings(bytestring: bytes, min: int = 10) -> str:
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
    process.stdin.write(bytestring)
    output = process.communicate()[0]
    return output.decode("ascii").strip()


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
