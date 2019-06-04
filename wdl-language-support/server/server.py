### This file has been adopted from
### https://github.com/openlawlibrary/pygls/blob/master/examples/json-extension/server/server.py

from asyncio import get_event_loop, sleep

from cromwell_tools import api as cromwell_api
from cromwell_tools.cromwell_auth import CromwellAuth

from functools import wraps

from pygls.features import (
    CODE_ACTION,
    TEXT_DOCUMENT_DID_OPEN,
    TEXT_DOCUMENT_DID_SAVE,
    TEXT_DOCUMENT_DID_CLOSE,
)
from pygls.server import LanguageServer
from pygls.types import (
    CodeActionParams,
    ConfigurationItem,
    ConfigurationParams,
    Diagnostic,
    DidOpenTextDocumentParams,
    DidSaveTextDocumentParams,
    DidCloseTextDocumentParams,
    MessageType,
    Position,
    Range,
    TextDocumentItem,
)

import re, sys
from requests import HTTPError
from typing import Callable, List, Set
from urllib.parse import urlparse

import WDL

class Server(LanguageServer):
    SERVER_NAME = 'wdl'
    CONFIG_SECTION = SERVER_NAME

    CMD_RUN_WDL = SERVER_NAME + '.run'

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

async def _request(func: Callable):
    response = await _async(func)
    return response.json()

async def _get_client_config(ls: Server):
    config = await ls.get_configuration_async(ConfigurationParams([
        ConfigurationItem(section=Server.CONFIG_SECTION)
    ]))
    return config[0]

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


class RunWDLParams:
    def __init__(self, wdl_uri: str):
        self.wdl_uri = wdl_uri

@server.feature(CODE_ACTION)
@server.catch_error
async def code_action(ls: Server, params: CodeActionParams):
    return [{
        'title': 'Run WDL',
        'kind': Server.CMD_RUN_WDL,
        'command': {
            'command': Server.CMD_RUN_WDL,
            'arguments': [RunWDLParams(params.textDocument.uri)],
        },
    }]

@server.command(Server.CMD_RUN_WDL)
@server.catch_error
async def run_wdl(ls: Server, params: List[RunWDLParams]):
    wdl_uri = params[0].wdl_uri
    await _validate(ls, wdl_uri)
    wdl_path = urlparse(wdl_uri).path

    config = await _get_client_config(ls)
    auth = CromwellAuth.from_no_authentication(config.cromwell.url)
    workflow = await _request(lambda: cromwell_api.submit(
        auth, wdl_path, raise_for_status=True,
    ))
    id = workflow['id']

    title = 'Workflow {} for {}'.format(id, wdl_path)
    _progress(ls, 'start', {
        'id': id,
        'title': title,
        'cancellable': True,
        'message': workflow['status'],
    })

    status: str = ''
    while True:
        if status != workflow['status']:
            status = workflow['status']
            if status == 'Succeeded':
                message_type = MessageType.Info
            elif status in ('Aborting', 'Aborted'):
                message_type = MessageType.Warning
            elif status == 'Failed':
                message_type = MessageType.Error
            else:
                _progress(ls, 'report', {
                    'id': id,
                    'message': status,
                })
                continue

            _progress(ls, 'done', {
                'id': id,
            })
            message = '{}: {}'.format(title, status)
            return ls.show_message(message, message_type)

        await sleep(config.cromwell.pollSec)

        if id in cancel_workflows:
            workflow = await _request(lambda: cromwell_api.abort(
                id, auth, raise_for_status=True,
            ))
            cancel_workflows.remove(id)
            continue

        try:
            workflow = await _request(lambda: cromwell_api.status(
                id, auth, raise_for_status=True,
            ))
        except HTTPError as e:
            ls.show_message_log(str(e), MessageType.Error)

cancel_workflows: Set[str] = set()

def _progress(ls: Server, action: str, params):
    ls.send_notification('window/progress/' + action, params)

@server.feature('window/progress/cancel')
@server.catch_error
async def abort_workflow(ls: Server, params):
    cancel_workflows.add(params.id)
