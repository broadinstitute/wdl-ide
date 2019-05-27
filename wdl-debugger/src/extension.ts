import { promises as fs } from 'fs';
import * as path from 'path';

import {
	ExtensionContext,
	commands,
	window,
	workspace,
} from 'vscode';

import { submitWorkflow } from './cromwell';

const cmdRunWDL = 'extension.runWDL';
const cromwellBaseUriConfig = 'wdl-debugger.cromwell.baseUri';

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

			const resourceConfig = workspace.getConfiguration('', uri);
			let cromwellBaseUri = resourceConfig.get<string>(cromwellBaseUriConfig)!;

			const wdlPath = uri.fsPath;
			const { id, status } = await submitWorkflow(
				cromwellBaseUri,
				wdlPath,
				await getInputsPath(storagePath, wdlPath),
				await getOptionsPath(storagePath),
			);

			window.showInformationMessage(`${status} ${id}`);
		} catch (err) {
			window.showErrorMessage(err.message);
		}
	});

	context.subscriptions.push(disposable);
};

const getInputsPath = (storagePath: string, wdlPath: string) => {
	const fileName = path.basename(wdlPath, '.wdl') + `.inputs.json`;
	return getFilePath(storagePath, fileName);
};

const getOptionsPath = (storagePath: string) => {
	return getFilePath(storagePath, 'options.json');
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

export function deactivate() {}
