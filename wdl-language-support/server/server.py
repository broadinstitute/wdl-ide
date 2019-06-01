### This file has been adopted from
### https://github.com/openlawlibrary/pygls/blob/master/examples/json-extension/server/server.py

from pygls.features import (
    TEXT_DOCUMENT_DID_OPEN,
    TEXT_DOCUMENT_DID_SAVE,
    TEXT_DOCUMENT_DID_CLOSE,
)
from pygls.server import LanguageServer
from pygls.types import (
    Diagnostic,
    DidOpenTextDocumentParams,
    DidSaveTextDocumentParams,
    DidCloseTextDocumentParams,
    Position,
    Range,
)

import re
import sys
import WDL

class Server(LanguageServer):
    def __init__(self):
        super().__init__()

server = Server()

def _validate(ls, params):
    ls.show_message_log('Validating WDL...')

    uri = params.textDocument.uri
    diagnostics = _validate_wdl(ls, uri)
    ls.publish_diagnostics(uri, diagnostics)


def _validate_wdl(ls, uri):
    """Validates WDL file."""
    diagnostics = []

    try:
        a = WDL.load(uri)
        ls.show_message_log('Validated')
    except WDL.Error.SyntaxError as e:
        err = e.args[0]
        match = re.match(r"\(.*\) (.*) at line (\d+) col (\d+)", err)
        msg = match.group(1)
        line = int(match.group(2))
        col = int(match.group(3))

        d = Diagnostic(
            Range(
                Position(line-1, col-1),
                Position(line-1, sys.maxsize)
            ),
            msg,
            source=type(server).__name__
        )

        diagnostics.append(d)

    return diagnostics


@server.feature(TEXT_DOCUMENT_DID_OPEN)
async def did_open(ls, params: DidOpenTextDocumentParams):
    """Text document did open notification."""
    ls.show_message('Text Document Did Open')
    _validate(ls, params)

@server.feature(TEXT_DOCUMENT_DID_SAVE)
def did_change(ls, params: DidSaveTextDocumentParams):
    """Text document did change notification."""
    _validate(ls, params)


@server.feature(TEXT_DOCUMENT_DID_CLOSE)
def did_close(server: Server, params: DidCloseTextDocumentParams):
    """Text document did close notification."""
    server.show_message('Text Document Did Close')
