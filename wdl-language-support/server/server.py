### This file has been adopted from
### https://github.com/openlawlibrary/pygls/blob/master/examples/json-extension/server/server.py

from pygls.features import (TEXT_DOCUMENT_DID_CHANGE,
                            TEXT_DOCUMENT_DID_CLOSE, TEXT_DOCUMENT_DID_OPEN)
from pygls.server import LanguageServer
from pygls.types import (Diagnostic,
                         DidChangeTextDocumentParams,
                         DidCloseTextDocumentParams, DidOpenTextDocumentParams,
                         Position, Range)

class Server(LanguageServer):
    def __init__(self):
        super().__init__()

server = Server()

def _validate(ls, params):
    ls.show_message_log('Validating WDL...')

    text_doc = ls.workspace.get_document(params.textDocument.uri)

    source = text_doc.source
    diagnostics = _validate_wdl(source) if source else []

    ls.publish_diagnostics(text_doc.uri, diagnostics)


def _validate_wdl(source):
    """Validates WDL file."""
    diagnostics = []

    try:
        pass
    except ValueError as err:
        msg = err.msg
        col = err.colno
        line = err.lineno

        d = Diagnostic(
            Range(
                Position(line-1, col-1),
                Position(line-1, col)
            ),
            msg,
            source=type(server).__name__
        )

        diagnostics.append(d)

    return diagnostics


@server.feature(TEXT_DOCUMENT_DID_CHANGE)
def did_change(ls, params: DidChangeTextDocumentParams):
    """Text document did change notification."""
    _validate(ls, params)


@server.feature(TEXT_DOCUMENT_DID_CLOSE)
def did_close(server: Server, params: DidCloseTextDocumentParams):
    """Text document did close notification."""
    server.show_message('Text Document Did Close')


@server.feature(TEXT_DOCUMENT_DID_OPEN)
async def did_open(ls, params: DidOpenTextDocumentParams):
    """Text document did open notification."""
    ls.show_message('Text Document Did Open')
    _validate(ls, params)
