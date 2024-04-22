### This file has been adopted from
### https://github.com/openlawlibrary/pygls/blob/master/examples/json-extension/server/server.py

import asyncio
import sys
from bisect import bisect
from functools import wraps
from importlib.metadata import version
from os import environ
from os import name as platform
from os import pathsep
from pathlib import Path
from threading import Timer
from time import sleep
from typing import (Callable, Dict, Iterable, List, Mapping, Optional, Set,
                    Tuple, TypedDict, Union)
from urllib.parse import urlparse

import WDL
from cromwell_tools import api as cromwell_api
from cromwell_tools.cromwell_auth import CromwellAuth
from cromwell_tools.utilities import download
from lsprotocol.types import (TEXT_DOCUMENT_CODE_ACTION,
                              TEXT_DOCUMENT_DEFINITION,
                              TEXT_DOCUMENT_DID_CHANGE, TEXT_DOCUMENT_DID_OPEN,
                              TEXT_DOCUMENT_DID_SAVE, TEXT_DOCUMENT_REFERENCES,
                              TEXT_DOCUMENT_WILL_SAVE,
                              WORKSPACE_DID_CHANGE_CONFIGURATION,
                              WORKSPACE_DID_CHANGE_WATCHED_FILES,
                              CodeActionParams, ConfigurationItem,
                              ConfigurationParams, Diagnostic,
                              DiagnosticSeverity, DidChangeConfigurationParams,
                              DidChangeTextDocumentParams,
                              DidChangeWatchedFilesParams,
                              DidOpenTextDocumentParams,
                              DidSaveTextDocumentParams, FileChangeType,
                              Location, MessageType, Position, Range,
                              TextDocumentPositionParams,
                              WillSaveTextDocumentParams)
from pygls.server import LanguageServer
from requests import HTTPError
from WDL import Lint, SourceNode, SourcePosition

PARSE_DELAY_SEC = 0.5  # delay parsing of WDL until no more keystrokes are sent


class Server(LanguageServer):
    NAME = 'wdl'
    CONFIG_SECTION = NAME

    CMD_RUN_WDL = NAME + '.run'

    def __init__(self):
        super().__init__(Server.NAME, version('wdl-lsp'))
        self.wdl_paths: Dict[str, Set[str]] = dict()
        self.wdl_types: Dict[str, Dict[str, SourcePosition]] = dict()
        self.wdl_defs: Dict[str, Mapping[SourcePosition, SourcePosition]] = dict()
        self.wdl_refs: Dict[str, Dict[SourcePosition, List[SourcePosition]]] = dict()
        self.wdl_symbols: Dict[str, List[SourcePosition]] = dict()
        self.aborting_workflows: Set[str] = set()

    def catch_error(self, log=False):
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
    config = ls.get_configuration(
        ConfigurationParams([ConfigurationItem(section=Server.CONFIG_SECTION)])
    ).result()
    return config[0]


# https://gist.github.com/walkermatt/2871026
def debounce(delay_sec: float, id_arg: Union[int, str]):
    """Decorator that will postpone a functions
    execution until after wait seconds
    have elapsed since the last time it was invoked."""

    def decorator(func: Callable):
        @wraps(func)
        def debounced(*args, **kwargs):
            if not hasattr(debounced, 'timers'):
                debounced.timers = dict()
            id = args[id_arg] if isinstance(id_arg, int) else kwargs[id_arg]
            if id in debounced.timers:
                debounced.timers[id].cancel()
            timer = Timer(delay_sec, lambda: func(*args, **kwargs))
            getattr(debounced, 'timers')[id] = timer
            timer.start()

        return debounced

    return decorator


@debounce(PARSE_DELAY_SEC, 1)
def parse_wdl(ls: Server, uri: str):
    ls.show_message_log('Validating ' + uri, MessageType.Info)
    diagnostics, wdl = _parse_wdl(ls, uri)
    ls.publish_diagnostics(uri, diagnostics)
    ls.show_message_log(
        '{} {}'.format('Valid' if wdl else 'Invalid', uri),
        MessageType.Info if wdl else MessageType.Warning,
    )


def _parse_wdl(ls: Server, uri: str):
    try:
        paths = _get_wdl_paths(ls, uri)
        doc = asyncio.run(WDL.load_async(uri, path=paths, read_source=_read_source(ls)))

        types = _get_types(doc.children, dict())
        ls.wdl_types[uri] = types
        ls.wdl_defs[uri], ls.wdl_refs[uri] = _get_links(
            doc.children, types, dict(), dict()
        )
        ls.wdl_symbols[uri] = sorted(_get_symbols(doc.children, []))

        return list(_lint_wdl(ls, doc)), doc

    except WDL.Error.MultipleValidationErrors as errs:
        return [_diagnostic_err(e) for e in errs.exceptions], None

    except WDLError as e:
        return [_diagnostic_err(e)], None

    except Exception as e:
        ls.show_message_log(str(e), MessageType.Error)
        return [], None


def _read_source(ls: Server):
    async def read_source(uri: str, path, importer):
        uri = await WDL.resolve_file_import(uri, path, importer)
        if uri.startswith('/'):
            uri = 'file://' + uri
        source = ls.workspace.get_document(uri).source
        return WDL.ReadSourceResult(source_text=source, abspath=uri)

    return read_source


def _get_symbols(nodes: Iterable[SourceNode], symbols: List[SourcePosition]):
    for node in nodes:
        symbols.append(node.pos)
        _get_symbols(node.children, symbols)
    return symbols


# find SourcePosition as the minimum bounding box for cursor Position
def _find_symbol(ls: Server, uri: str, p: Position):
    if uri not in ls.wdl_symbols:
        return
    symbols = ls.wdl_symbols[uri]

    best_score = (sys.maxsize, sys.maxsize)
    best_sym: Optional[SourcePosition] = None

    line = p.line + 1
    col = p.character + 1

    min_pos = SourcePosition(uri, uri, line, 0, line, 0)
    i = bisect(symbols, min_pos)

    while i < len(symbols):
        sym = symbols[i]
        if sym.line > line or (sym.line == line and sym.column > col):
            break
        elif sym.end_line > line or (sym.end_line == line and sym.end_column >= col):
            score = (sym.end_line - sym.line, sym.end_column - sym.column)
            if score <= best_score:
                best_score = score
                best_sym = sym
        i += 1
    return best_sym


def _get_types(nodes: Iterable[SourceNode], types: Dict[str, SourcePosition]):
    for node in nodes:
        if isinstance(node, WDL.Tree.StructTypeDef):
            types[node.type_id] = node.pos
        _get_types(node.children, types)
    return types


def _get_links(
    nodes: Iterable[SourceNode],
    types: Dict[str, SourcePosition],
    defs: Dict[SourcePosition, SourcePosition],
    refs: Dict[SourcePosition, List[SourcePosition]],
):
    for node in nodes:
        source: Optional[SourcePosition] = None
        if isinstance(node, WDL.Tree.Call) and node.callee is not None:
            source = node.callee.pos
        elif isinstance(node, WDL.Tree.Decl) and isinstance(
            node.type, WDL.Type.StructInstance
        ):
            source = types[node.type.type_id]
        elif isinstance(node, WDL.Expr.Ident):
            ref = node.referee
            if isinstance(ref, WDL.Tree.Gather):
                source = ref.final_referee.pos
            else:
                source = getattr(ref, 'pos', None)
        if source is not None:
            defs[node.pos] = source
            refs.setdefault(source, []).append(node.pos)
        _get_links(node.children, types, defs, refs)
    return defs, refs


SourceLinks = Union[SourcePosition, List[SourcePosition]]


def _find_links(
    ls: Server,
    uri: str,
    pos: Position,
    links: Mapping[str, Mapping[SourcePosition, SourceLinks]],
):
    symbol = _find_symbol(ls, uri, pos)
    if (symbol is None) or (uri not in links):
        return
    symbols = links[uri]
    if symbol in symbols:
        return symbols[symbol]


def _find_def(ls: Server, uri: str, pos: Position):
    link = _find_links(ls, uri, pos, ls.wdl_defs)
    if isinstance(link, SourcePosition):
        return Location(link.abspath, _get_range(link))


def _find_refs(ls: Server, uri: str, pos: Position):
    links = _find_links(ls, uri, pos, ls.wdl_refs)
    if isinstance(links, list):
        return [Location(link.abspath, _get_range(link)) for link in links]


def _lint_wdl(ls: Server, doc: WDL.Tree.Document):
    _check_linter_path()
    warnings = Lint.collect(Lint.lint(doc, descend_imports=False))
    _check_linter_available(ls)
    for pos, _, msg, _ in warnings:
        yield _diagnostic(msg, pos, DiagnosticSeverity.Warning)


def _check_linter_path():
    if getattr(_check_linter_path, 'skip', False):
        return

    LOCAL_BIN = '/usr/local/bin'
    PATH = environ['PATH'].split(pathsep)

    if platform == 'posix' and LOCAL_BIN not in PATH:
        environ['PATH'] = pathsep.join([LOCAL_BIN] + PATH)
    _check_linter_path.skip = True


def _check_linter_available(ls: Server):
    if getattr(_check_linter_available, 'skip', False):
        return

    if not Lint._shellcheck_available:
        ls.show_message(
            """
            WDL task command linter is not available on the system PATH.
            Please install ShellCheck and/or add it to the PATH:
            https://github.com/koalaman/shellcheck#installing
        """,
            MessageType.Warning,
        )
    _check_linter_available.skip = True


def _get_wdl_paths(ls: Server, wdl_uri: str, reuse_paths=True) -> List[str]:
    ws = ls.workspace
    if ws.folders:
        ws_uris = [f for f in ws.folders if wdl_uri.startswith(f)]
    elif ws.root_uri:
        ws_uris = [ws.root_uri]
    else:
        ws_uris = []
    wdl_paths: Set[str] = set()
    for ws_uri in ws_uris:
        if reuse_paths and (ws_uri in ls.wdl_paths):
            ws_paths = ls.wdl_paths[ws_uri]
        else:
            ws_paths: Set[str] = set()
            ws_root = Path(urlparse(ws_uri).path)
            for p in ws_root.rglob('*.wdl'):
                ws_paths.add(str(p.parent))
            ls.wdl_paths[ws_uri] = ws_paths
        wdl_paths.update(ws_paths)
    return list(wdl_paths)


WDLError = Union[
    WDL.Error.ImportError, WDL.Error.SyntaxError, WDL.Error.ValidationError
]


def _diagnostic(
    msg: str, pos: Optional[SourcePosition] = None, severity=DiagnosticSeverity.Error
):
    return Diagnostic(_get_range(pos), msg, severity=severity)


def _get_range(p: Optional[SourcePosition] = None):
    if p is None:
        return Range(
            Position(0, sys.maxsize),
            Position(0, sys.maxsize),
        )
    else:
        return Range(
            Position(p.line - 1, p.column - 1),
            Position(p.end_line - 1, p.end_column - 1),
        )


def _diagnostic_err(e: WDLError):
    cause = ': {}'.format(e.__cause__) if e.__cause__ else ''
    msg = str(e) + cause
    return _diagnostic(msg, e.pos)


@server.thread()
@server.feature(TEXT_DOCUMENT_DID_OPEN)
@server.catch_error()
def did_open(ls: Server, params: DidOpenTextDocumentParams):
    parse_wdl(ls, params.text_document.uri)


@server.thread()
@server.feature(TEXT_DOCUMENT_DID_CHANGE)
@server.catch_error()
def did_change(ls: Server, params: DidChangeTextDocumentParams):
    parse_wdl(ls, params.text_document.uri)


@server.thread()
@server.feature(TEXT_DOCUMENT_DID_SAVE)
@server.catch_error()
def did_save(ls: Server, params: DidSaveTextDocumentParams):
    pass


@server.thread()
@server.feature(TEXT_DOCUMENT_WILL_SAVE)
@server.catch_error()
def will_save(ls: Server, params: WillSaveTextDocumentParams):
    pass


@server.feature(WORKSPACE_DID_CHANGE_CONFIGURATION)
def did_change_configuration(ls: Server, params: DidChangeConfigurationParams):
    pass


@server.thread()
@server.feature(WORKSPACE_DID_CHANGE_WATCHED_FILES)
@server.catch_error()
def did_change_watched_files(ls: Server, params: DidChangeWatchedFilesParams):
    for change in params.changes:
        if change.type in [
            FileChangeType.Created,
            FileChangeType.Deleted,
        ] and change.uri.endswith('.wdl'):
            _get_wdl_paths(ls, change.uri, reuse_paths=False)


@server.thread()
@server.feature(TEXT_DOCUMENT_DEFINITION)
@server.catch_error()
def goto_TEXT_DOCUMENT_DEFINITION(ls: Server, params: TextDocumentPositionParams):
    return _find_def(ls, params.text_document.uri, params.position)


@server.thread()
@server.feature(TEXT_DOCUMENT_REFERENCES)
@server.catch_error()
def find_TEXT_DOCUMENT_REFERENCES(ls: Server, params: TextDocumentPositionParams):
    return _find_refs(ls, params.text_document.uri, params.position)


class RunWDLParams(TypedDict):
    wdl_uri: str


@server.feature(TEXT_DOCUMENT_CODE_ACTION)
@server.catch_error()
def code_action(ls: Server, params: CodeActionParams):
    return [
        {
            'title': 'Run WDL',
            'kind': Server.CMD_RUN_WDL,
            'command': {
                'command': Server.CMD_RUN_WDL,
                'arguments': [RunWDLParams(wdl_uri=params.text_document.uri)],
            },
        }
    ]


@server.thread()
@server.command(Server.CMD_RUN_WDL)
@server.catch_error()
def run_wdl(ls: Server, params: Tuple[RunWDLParams]):
    wdl_uri = params[0]['wdl_uri']
    wdl_path = urlparse(wdl_uri).path

    _, wdl = _parse_wdl(ls, wdl_uri)
    if not wdl:
        return ls.show_message(
            'Unable to submit: WDL contains error(s)', MessageType.Error
        )

    cromwell = _get_client_config(ls)['cromwell']
    auth = CromwellAuth.from_no_authentication(cromwell['url'])  # type: ignore
    workflow = cromwell_api.submit(  # type: ignore
        auth,
        wdl_path,
        raise_for_status=True,
    ).json()
    id = workflow['id']

    title = 'Workflow {} for {}'.format(id, wdl_path)
    _progress(
        ls,
        'start',
        {
            'id': id,
            'title': title,
            'cancellable': True,
            'message': workflow['status'],
        },
    )

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
                _progress(
                    ls,
                    'report',
                    {
                        'id': id,
                        'message': status,
                    },
                )
                continue

            _progress(
                ls,
                'done',
                {
                    'id': id,
                },
            )
            message = '{}: {}'.format(title, status)
            ls.show_message(message, message_type)

            diagnostics = _parse_failures(wdl, id, auth)
            return ls.publish_diagnostics(wdl_uri, diagnostics)

        sleep(cromwell['pollSec'])

        if id in ls.aborting_workflows:
            workflow = cromwell_api.abort(  # type: ignore
                id,
                auth,
                raise_for_status=True,
            ).json()
            ls.aborting_workflows.remove(id)
            continue

        try:
            workflow = cromwell_api.status(  # type: ignore
                id,
                auth,
                raise_for_status=True,
            ).json()
        except HTTPError as e:
            ls.show_message_log(str(e), MessageType.Error)


def _progress(ls: Server, action: str, params):
    ls.send_notification('window/progress/' + action, params)


@server.feature('window/progress/cancel')
def abort_workflow(ls: Server, params):
    ls.aborting_workflows.add(params.id)


def _parse_failures(wdl: WDL.Tree.Document, id: str, auth: CromwellAuth):
    workflow = cromwell_api.metadata(  # type: ignore
        id,
        auth,
        includeKey=['status', 'executionStatus', 'failures', 'stderr'],
        expandSubWorkflows=True,
        raise_for_status=True,
    ).json()
    if not wdl.workflow or workflow['status'] != 'Failed':
        return

    calls = workflow['calls']
    if calls:
        diagnostics: List[Diagnostic] = []

        for call, attempts in calls.items():
            for attempt in attempts:
                if attempt['executionStatus'] == 'Failed':
                    pos = _find_call(wdl.workflow.children, wdl.workflow.name, call)
                    failures = _collect_failures(attempt['failures'], [])

                    stderr = _download(attempt['stderr'])
                    if stderr is not None:
                        failures.append(stderr)

                    msg = '\n\n'.join(failures)
                    diagnostics.append(_diagnostic(msg, pos))
        return diagnostics
    else:
        failures = _collect_failures(workflow['failures'], [])
        msg = '\n\n'.join(failures)
        return [_diagnostic(msg)]


def _collect_failures(causedBy: List[dict], failures: List[str]):
    for failure in causedBy:
        if failure['causedBy']:
            _collect_failures(failure['causedBy'], failures)
        failures.append(failure['message'])
    return failures


def _find_call(elements: Iterable[SourceNode], wf_name: str, call_name: str):
    found: Optional[SourcePosition] = None
    for el in elements:
        if found:
            break
        elif (
            isinstance(el, WDL.Tree.Call)
            and '{}.{}'.format(wf_name, el.name) == call_name
        ):
            found = el.pos
        elif isinstance(el, WDL.Tree.Conditional) or isinstance(el, WDL.Tree.Scatter):
            found = _find_call(el.children, wf_name, call_name)
    return found


@server.catch_error(log=True)
def _download(url: str):
    text = download(url)
    if isinstance(text, str):
        return text
    return str(text, 'utf-8')
