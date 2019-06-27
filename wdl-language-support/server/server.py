### This file has been adopted from
### https://github.com/openlawlibrary/pygls/blob/master/examples/json-extension/server/server.py

from cromwell_tools import api as cromwell_api
from cromwell_tools.cromwell_auth import CromwellAuth
from cromwell_tools.utilities import download

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
from time import sleep
from typing import Callable, List, Set, Tuple, Union
from urllib.parse import urlparse

import WDL

class Server(LanguageServer):
    SERVER_NAME = 'wdl'
    CONFIG_SECTION = SERVER_NAME

    CMD_RUN_WDL = SERVER_NAME + '.run'

    def __init__(self):
        super().__init__()

    def catch_error(self, log = False):
        def decorator(func: Callable):
            @wraps(func)
            def wrapper(*args, **kwargs):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if log:
                        self.show_message_log(str(e), MessageType.Error)
                    else:
                        self.show_message(str(e), MessageType.Error)
            return wrapper
        return decorator

server = Server()

def _get_client_config(ls: Server):
    config = ls.get_configuration(ConfigurationParams([
        ConfigurationItem(section=Server.CONFIG_SECTION)
    ])).result()
    return config[0]

def parse_wdl(ls: Server, uri: str):
    ls.show_message_log('Validating WDL...')

    diagnostics, wdl = _parse_wdl(uri)

    ls.show_message_log('Validated')
    ls.publish_diagnostics(uri, diagnostics)
    return diagnostics, wdl

def _parse_wdl(uri: str):
    try:
        wdl = WDL.load(uri)
        return [], wdl

    except WDL.Error.MultipleValidationErrors as errs:
        return [_diagnostic_err(e) for e in errs.exceptions], None

    except WDLError as e:
        return [_diagnostic_err(e)], None

WDLError = (WDL.Error.ImportError, WDL.Error.SyntaxError, WDL.Error.ValidationError)

def _diagnostic(msg: str, line = 1, col = 1, end_line = None, end_col = sys.maxsize):
    if end_line is None:
        end_line = line
    return Diagnostic(
        Range(
            Position(line - 1, col - 1),
            Position(end_line - 1, end_col - 1),
        ),
        msg,
    )

def _diagnostic_pos(msg: str, pos: WDL.SourcePosition):
    return _diagnostic(msg, pos.line, pos.column, pos.end_line, pos.end_column)

def _diagnostic_err(e: WDLError):
    cause = ': {}'.format(e.__cause__.strerror) if e.__cause__ else ''
    msg = str(e) + cause
    return _diagnostic_pos(msg, e.pos)


@server.thread()
@server.feature(TEXT_DOCUMENT_DID_OPEN)
@server.catch_error()
def did_open(ls: Server, params: DidOpenTextDocumentParams):
    """Text document did open notification."""
    uri = params.textDocument.uri
    ls.show_message_log('Opened {}'.format(uri))
    parse_wdl(ls, uri)

@server.thread()
@server.feature(TEXT_DOCUMENT_DID_SAVE)
@server.catch_error()
def did_save(ls: Server, params: DidSaveTextDocumentParams):
    """Text document did change notification."""
    uri = params.textDocument.uri
    ls.show_message_log('Saved {}'.format(uri))
    parse_wdl(ls, uri)

@server.feature(TEXT_DOCUMENT_DID_CLOSE)
@server.catch_error()
def did_close(ls: Server, params: DidCloseTextDocumentParams):
    """Text document did close notification."""
    uri = params.textDocument.uri
    ls.show_message_log('Closed {}'.format(uri))

class RunWDLParams:
    def __init__(self, wdl_uri: str):
        self.wdl_uri = wdl_uri

@server.feature(CODE_ACTION)
@server.catch_error()
def code_action(ls: Server, params: CodeActionParams):
    return [{
        'title': 'Run WDL',
        'kind': Server.CMD_RUN_WDL,
        'command': {
            'command': Server.CMD_RUN_WDL,
            'arguments': [RunWDLParams(params.textDocument.uri)],
        },
    }]

@server.thread()
@server.command(Server.CMD_RUN_WDL)
@server.catch_error()
def run_wdl(ls: Server, params: Tuple[RunWDLParams]):
    wdl_uri = params[0].wdl_uri
    wdl_path = urlparse(wdl_uri).path

    diagnostics, wdl = parse_wdl(ls, wdl_uri)
    if diagnostics:
        return ls.show_message('Unable to submit: WDL contains error(s)', MessageType.Error)

    config = _get_client_config(ls)
    auth = CromwellAuth.from_no_authentication(config.cromwell.url)
    workflow = cromwell_api.submit(
        auth, wdl_path, raise_for_status=True,
    ).json()
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
            ls.show_message(message, message_type)

            diagnostics = _parse_failures(wdl, wdl_uri, id, auth)
            return ls.publish_diagnostics(wdl_uri, diagnostics)

        sleep(config.cromwell.pollSec)

        if id in cancel_workflows:
            workflow = cromwell_api.abort(
                id, auth, raise_for_status=True,
            ).json()
            cancel_workflows.remove(id)
            continue

        try:
            workflow = cromwell_api.status(
                id, auth, raise_for_status=True,
            ).json()
        except HTTPError as e:
            ls.show_message_log(str(e), MessageType.Error)

cancel_workflows: Set[str] = set()

def _progress(ls: Server, action: str, params):
    ls.send_notification('window/progress/' + action, params)

@server.feature('window/progress/cancel')
def abort_workflow(ls: Server, params):
    cancel_workflows.add(params.id)

def _parse_failures(wdl: WDL.Document, wdl_uri: str, id: str, auth: CromwellAuth):
    workflow = cromwell_api.metadata(
        id, auth,
        includeKey=['status', 'executionStatus', 'failures', 'stderr'],
        expandSubWorkflows=True,
        raise_for_status=True,
    ).json()
    if workflow['status'] != 'Failed':
        return

    calls = workflow['calls']
    if calls:
        diagnostics: List[Diagnostic] = []
        elements = wdl.workflow.elements

        for call, attempts in calls.items():
            for attempt in attempts:
                if attempt['executionStatus'] == 'Failed':
                    pos = _find_call(wdl.workflow.elements, wdl.workflow.name, call)
                    failures = _collect_failures(attempt['failures'], [])

                    stderr = _download(attempt['stderr'])
                    if stderr is not None:
                        failures.append(stderr)

                    msg = '\n\n'.join(failures)
                    diagnostics.append(_diagnostic_pos(msg, pos))
        return diagnostics
    else:
        failures = _collect_failures(workflow['failures'], [])
        msg = '\n\n'.join(failures)
        return [_diagnostic(msg)]

class CausedBy:
    def __init__(self, causedBy: List['CausedBy'], message: str):
        self.causedBy = causedBy
        self.message = message

def _collect_failures(causedBy: List[CausedBy], failures: List[str]):
    for failure in causedBy:
        if failure['causedBy']:
            _collect_failures(failure['causedBy'], failures)
        failures.append(failure['message'])
    return failures

WorkflowElements = List[Union[WDL.Decl, WDL.Call, WDL.Scatter, WDL.Conditional]]

def _find_call(elements: WorkflowElements, wf_name: str, call_name: str):
    found: WDL.SourcePosition = None
    for el in elements:
        if found:
            break
        elif isinstance(el, WDL.Call) and '{}.{}'.format(wf_name, el.name) == call_name:
            found = el.pos
        elif isinstance(el, WDL.Conditional) or isinstance(el, WDL.Scatter):
            found = _find_call(el.elements, wf_name, call_name)
    return found

@server.catch_error(log=True)
def _download(url: str):
    return str(download(url), 'utf-8')
