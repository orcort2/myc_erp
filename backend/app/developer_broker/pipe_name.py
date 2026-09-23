"""DEV-1B: logical Named Pipe name -> local pipe path.

Configuration supplies only a LOGICAL name (e.g. ``MYCDeveloperBroker``);
the path is always built here as ``\\\\.\\pipe\\<name>`` -- local server
(``.``), pipe namespace only. A full path, a UNC/remote host, another
namespace, path separators, ``..``, ``:`` or a DOS device name is rejected
instead of being "cleaned up".
"""

import re

from app.developer_broker.protocol import BrokerConfigurationError


PIPE_NAME_MAX_LENGTH = 64
LOCAL_PIPE_PREFIX = "\\\\.\\pipe\\"
# Letter first; then letters, digits, '_' or '-'. No '.', ':', '/', '\\',
# spaces or anything else, so no traversal, namespace or host syntax fits.
_PIPE_NAME = re.compile(r"[A-Za-z][A-Za-z0-9_-]{2,63}")
_DOS_DEVICE_NAME = re.compile(r"(CON|PRN|AUX|NUL|CONIN|CONOUT|CLOCK|COM[0-9]+|LPT[0-9]+)", re.IGNORECASE)


def validate_pipe_name(value: str | None) -> str:
    name = value or ""
    if not name.strip():
        raise BrokerConfigurationError("pipe_name_missing")
    if (
        len(name) > PIPE_NAME_MAX_LENGTH
        or not _PIPE_NAME.fullmatch(name)
        or _DOS_DEVICE_NAME.fullmatch(name)
    ):
        raise BrokerConfigurationError("pipe_name_invalid")
    return name


def local_pipe_path(name: str) -> str:
    """Only ever the local machine's pipe namespace."""
    return LOCAL_PIPE_PREFIX + validate_pipe_name(name)
