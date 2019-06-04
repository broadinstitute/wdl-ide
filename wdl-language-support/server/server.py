### This file has been adopted from
### https://github.com/openlawlibrary/pygls/blob/master/examples/json-extension/server/server.py

from asyncio import get_event_loop
from functools import wraps

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
    MessageType,
    Position,
    Range,
    TextDocumentItem,
)

import re
import sys
from typing import Callable

import WDL

class Server(LanguageServer):
    def __init__(self):
        super().__init__()

    def catch_error(self, func: Callable) -> Callable:
        @wraps(func)
        async def decorator(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                self.show_message(str(e), MessageType.Error)
        return decorator

server = Server()

def _async(func: Callable):
    return get_event_loop().run_in_executor(None, func)

async def _validate(ls: Server, uri: str):
    ls.show_message_log('Validating WDL...')

    diagnostics = await _validate_wdl(ls, uri)
    ls.publish_diagnostics(uri, diagnostics)

async def _validate_wdl(ls: Server, uri: str):
    try:
        await _async(lambda: WDL.load(uri))
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
    return re.match("^\(.*\) (.*)", str(e)).group(1)

def _match_err_and_pos(e: Exception):
    match = re.match("^\(.*\) (.*) at line (\d+) col (\d+)", str(e))
    return match.group(1), int(match.group(2)), int(match.group(3))


@server.feature(TEXT_DOCUMENT_DID_OPEN)
@server.catch_error
async def did_open(ls: Server, params: DidOpenTextDocumentParams):
    """Text document did open notification."""
    uri = params.textDocument.uri
    ls.show_message_log('Opened {}'.format(uri))
    await _validate(ls, uri)

@server.feature(TEXT_DOCUMENT_DID_SAVE)
@server.catch_error
async def did_save(ls: Server, params: DidSaveTextDocumentParams):
    """Text document did change notification."""
    uri = params.textDocument.uri
    ls.show_message_log('Saved {}'.format(uri))
    await _validate(ls, uri)

@server.feature(TEXT_DOCUMENT_DID_CLOSE)
@server.catch_error
def did_close(ls: Server, params: DidCloseTextDocumentParams):
    """Text document did close notification."""
    uri = params.textDocument.uri
    ls.show_message_log('Closed {}'.format(uri))
