/* -------------------------------------------------------------------------
 * Original work Copyright (c) Microsoft Corporation. All rights reserved.
 * Original work licensed under the MIT License.
 * See ThirdPartyNotices.txt in the project root for license information.
 * All modifications Copyright (c) Open Law Library. All rights reserved.
 *
 * Licensed under the Apache License, Version 2.0 (the "License")
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http: // www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 * ----------------------------------------------------------------------- */
"use strict";

import { execFile } from "child_process";
import * as fs from "fs";
import * as path from "path";
import { ExtensionContext, window, workspace } from "vscode";
import { LanguageClient, LanguageClientOptions, ServerOptions } from "vscode-languageclient/node";

const language = "wdl";

const log = window.createOutputChannel("WDL Language Server");

const version: string = require("../package.json").version;
log.appendLine(`WDL Language Server version: ${version}`);

function getClientOptions(): LanguageClientOptions {
  return {
    // Register the server for WDL documents
    documentSelector: [
      { scheme: "file", language },
    ],
    outputChannel: log,
    synchronize: {
      // Notify the server about changes to .wdl files contained in the workspace
      fileEvents: workspace.createFileSystemWatcher("**/*.wdl"),
    },
  };
}

function startLangServer(
  command: string, args: string[], cwd: string,
): LanguageClient {
  const serverOptions: ServerOptions = {
    args,
    command,
    options: { cwd },
  };

  return new LanguageClient(language, serverOptions, getClientOptions());
}

async function exec(cmd: string, ...args: string[]) {
  return new Promise<void>(resolve => {
    execFile(cmd, args, (err, stdout, stderr) => {
      log.appendLine(`${cmd} ${args.join(" ")}`);
      if (err) {
        log.appendLine(err.message);
      }
      log.appendLine(stdout);
      log.appendLine(stderr);
      if (err) {
        log.show();
      }
      resolve();
    });
  });
}

let client: LanguageClient;

export async function activate(context: ExtensionContext) {
  const cwd = path.join(__dirname, "../");

  const venvPath = path.join(__dirname, '.venv');
  if (!fs.existsSync(venvPath)) {
    const pythonPath = workspace.getConfiguration(language).get<string>("pythonPath")!;
    await exec(pythonPath, "-m", "venv", venvPath);
  }

  const installArgs: string[] = [];
  if (process.env.VSCODE_DEBUG_MODE === "true") {
    installArgs.push(path.join(__dirname, '..', '..', '..', 'server'));
  } else {
    installArgs.push("--upgrade", "wdl-lsp");
  }
  const pythonPath = path.join(venvPath, 'bin', 'python');
  await exec(pythonPath, "-m", "pip", "install", ...installArgs);

  client = startLangServer(pythonPath, ["-m", "wdl_lsp"], cwd);
  client.registerProposedFeatures();
  await client.start();
}

export function deactivate() {
  if (client) {
    return client.stop();
  }
}
