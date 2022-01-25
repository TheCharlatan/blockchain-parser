import string
import subprocess
import magic
import imghdr


def gnu_strings(bytestring: bytes, min: int = 10) -> str:
    """Find and return a string with the specified minimum size."""
    cmd = "strings -n {}".format(min)
    process = subprocess.Popen(
        cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.PIPE)
    process.stdin.write(bytestring)
    output = process.communicate()[0]
    return output.decode("ascii").strip()


def find_file_with_magic(bytestring: bytes) -> None:
    res = magic.from_buffer(bytestring)
    for op in bytestring:
        if type(op) is int:
            continue
        res = magic.from_buffer(op)
        res = magic.from_buffer(op[1:])
        print(res)


def find_file_with_imghdr(bytestring: bytes) -> str:
    res = imghdr.what('', bytestring)
    if res:
        return res
    # try again with a potential padding byte removed
    res = imghdr.what('', bytestring[1:])
    if res:
        return res
    return ''


def native_strings(bytestring: bytes, min: int = 10) -> str:
    result = ""
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
