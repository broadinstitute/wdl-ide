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
    try:
        a = WDL.load(uri)
        ls.show_message_log('Validated')

    except WDL.Error.SyntaxError as e:
        err = e.args[0]
        match = re.match("^\(.*\) (.*) at line (\d+) col (\d+)", err)
        msg = match.group(1)
        line = int(match.group(2))
        col = int(match.group(3))
        return [_get_diagnostic(msg, line, col, line, sys.maxsize)]

    except WDL.Error.ValidationError as e:
        return [_add_validaton_error(e)]

    except WDL.Error.MultipleValidationErrors as errs:
        return [_add_validaton_error(e) for e in errs.exceptions]

    return []

def _get_diagnostic(msg, line, col, end_line, end_col):
    return Diagnostic(
        Range(
            Position(line - 1, col - 1),
            Position(end_line - 1, end_col - 1)
        ),
        msg,
        source=type(server).__name__
    )

def _add_validaton_error(e: WDL.Error.ValidationError):
    err = e.args[0]
    msg = re.match("^\(.*\) (.*)", err).group(1)
    pos = e.pos
    return _get_diagnostic(msg, pos.line, pos.column, pos.end_line, pos.end_column)

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
