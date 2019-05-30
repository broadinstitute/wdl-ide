import { promises as fs } from 'fs';
import * as path from 'path';
import {
	ExtensionContext,
	ProgressLocation,
	Uri,
	commands,
	window,
	workspace,
} from 'vscode';

import {
	WorkflowResponse,
	abortWorkflow,
	getWorklowStatus,
	postWorkflow,
} from './cromwell';

const cmdRunWDL = 'extension.runWDL';
const cromwellBaseUriConfig = 'wdl-debugger.cromwell.baseUri';
const cromwellPollMsecConfig = 'wdl-debugger.cromwell.pollMsec';

export const activate = async (context: ExtensionContext) => {
	const storagePath = context.storagePath!;

	try {
		await fs.mkdir(storagePath!);
	} catch (err) {
		if (err.code !== 'EEXIST') {
			throw err;
		}
	}

	const disposable = commands.registerTextEditorCommand(cmdRunWDL, async (
		{ document: { uri, languageId } },
	) => {
		try {
			if (languageId !== 'wdl') {
				throw Error('This command is only valid for WDL files!');
			}

			const cromwellBaseUri = getConfig<string>(uri, cromwellBaseUriConfig);
			const cromwellPollMsec = getConfig<number>(uri, cromwellPollMsecConfig);
			const wdlPath = uri.fsPath;

			await runAndWait(
				cromwellBaseUri, cromwellPollMsec, storagePath, wdlPath,
			);
		} catch (err) {
			showError(err);
		}
	});

	context.subscriptions.push(disposable);
};

const getConfig = <T>(uri: Uri | undefined, section: string) => {
	const config = workspace.getConfiguration('', uri);
	return config.get<T>(section)!;
};

const runAndWait = async (
	cromwellBaseUri: string,
	cromwellPollMsec: number,
	storagePath: string,
	wdlPath: string,
) => {
	const { id, status } = await postWorkflow(
		cromwellBaseUri,
		wdlPath,
		await getInputsPath(storagePath, wdlPath),
		await getOptionsPath(storagePath),
	);

	const title = `Workflow ${id} for ${path.basename(wdlPath)}`;

	return window.withProgress({
		title,
		location: ProgressLocation.Notification,
		cancellable: true,
	}, async (progress, token) => {
		return new Promise<WorkflowResponse>(resolve => {
			const interval = setInterval(async () => {
				try {
					const { status } = await getWorklowStatus(cromwellBaseUri, id);
					checkStopPolling(status);
				} catch (err) {
					showError(err);
				}
			}, cromwellPollMsec);

			let oldStatus = '';
			const checkStopPolling = (status: string) => {
				const message = `${title}: ${status}`;
				switch (status) {
					case 'Succeeded':
						window.showInformationMessage(message); break;
					case 'Aborting': case 'Aborted':
						window.showWarningMessage(message); break;
					case 'Failed':
						window.showErrorMessage(message); break;
					default:
						if (status !== oldStatus) {
							progress.report({
								message: status,
							});
						}
						oldStatus = status;
						return;
				}
				clearInterval(interval);
				resolve({ id, status });
			};

			checkStopPolling(status);

			token.onCancellationRequested(async () => {
				const { status } = await abortWorkflow(cromwellBaseUri, id);
				checkStopPolling(status);
			});
		});
	});
};

const getInputsPath = (storagePath: string, wdlPath: string) => {
	const fileName = path.basename(wdlPath, '.wdl') + `.inputs.json`;
	return getFilePath(storagePath, fileName);
};

const getOptionsPath = async (storagePath: string) => {
	const path = await getFilePath(storagePath, 'options.json');
	console.log(path);
	return path;
};

const getFilePath = async (storagePath: string, fileName: string) => {
	const filePath = path.join(storagePath, fileName);
	try {
		await fs.writeFile(filePath, '{\n\n}', { flag: 'wx' });
	} catch (err) {
		if (err.code !== 'EEXIST') {
			throw err;
		}
	}
	return filePath;
};

const showError = (err: Error) => {
	return window.showErrorMessage(err.message);
};

export function deactivate() {}
