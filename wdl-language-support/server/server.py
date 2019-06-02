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
    TextDocumentItem,
)

import re
import sys
from typing import List
import WDL

class Server(LanguageServer):
    def __init__(self):
        super().__init__()

server = Server()

def _validate(ls: LanguageServer, doc: TextDocumentItem):
    ls.show_message_log('Validating WDL...')

    diagnostics = _validate_wdl(ls, doc.uri)
    ls.publish_diagnostics(doc.uri, diagnostics)

def _validate_wdl(ls: LanguageServer, uri: str):
    """Validates WDL file."""
    try:
        a = WDL.load(uri)
        ls.show_message_log('Validated')
        return []

    except WDL.Error.SyntaxError as e:
        msg, line, col = _match_err_and_pos(e)
        return [_diagnostic(msg, line, col, line, sys.maxsize)]

    except WDL.Error.ValidationError as e:
        return [_validation_diagnostic(e)]

    except WDL.Error.MultipleValidationErrors as errs:
        return [_validation_diagnostic(e) for e in errs.exceptions]

    except WDL.Error.ImportError as e:
        msg = '{}: {}'.format(_match_err(e), e.__cause__.strerror)
        return [_diagnostic(msg, 1, 1, 1, 2)]

def _diagnostic(msg, line, col, end_line, end_col):
    return Diagnostic(
        Range(
            Position(line - 1, col - 1),
            Position(end_line - 1, end_col - 1),
        ),
        msg,
    )

def _validation_diagnostic(e: WDL.Error.ValidationError):
    msg = _match_err(e)
    pos = e.pos
    return _diagnostic(msg, pos.line, pos.column, pos.end_line, pos.end_column)

def _match_err(e: Exception):
    return re.match("^\(.*\) (.*)", e.args[0]).group(1)

def _match_err_and_pos(e: Exception):
    match = re.match("^\(.*\) (.*) at line (\d+) col (\d+)", e.args[0])
    return match.group(1), int(match.group(2)), int(match.group(3))


@server.feature(TEXT_DOCUMENT_DID_OPEN)
async def did_open(ls: LanguageServer, params: DidOpenTextDocumentParams):
    """Text document did open notification."""
    ls.show_message('Text Document Did Open')
    _validate(ls, params.textDocument)


@server.feature(TEXT_DOCUMENT_DID_SAVE)
def did_change(ls: LanguageServer, params: DidSaveTextDocumentParams):
    """Text document did change notification."""
    _validate(ls, params.textDocument)


@server.feature(TEXT_DOCUMENT_DID_CLOSE)
def did_close(ls: LanguageServer, params: DidCloseTextDocumentParams):
    """Text document did close notification."""
    ls.show_message('Text Document Did Close')
