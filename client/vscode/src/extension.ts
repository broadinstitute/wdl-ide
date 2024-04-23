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
import * as net from "net";
import * as path from "path";
import { promisify } from "util";
import { ExtensionContext, workspace } from "vscode";
import { LanguageClient, LanguageClientOptions, ServerOptions } from "vscode-languageclient/node";

const version: string = require("../package.json").version;

const language = "wdl";

let client: LanguageClient;

function getClientOptions(): LanguageClientOptions {
  return {
    // Register the server for WDL documents
    documentSelector: [
      { scheme: "file", language },
    ],
    outputChannelName: "WDL Language Server",
    synchronize: {
      // Notify the server about changes to .wdl files contained in the workspace
      fileEvents: workspace.createFileSystemWatcher("**/*.wdl"),
    },
  };
}

function isStartedInDebugMode(): boolean {
  return process.env.VSCODE_DEBUG_MODE === "true";
}

function startLangServerTCP(addr: number): LanguageClient {
  const serverOptions: ServerOptions = () => {
    return new Promise((resolve, reject) => {
      const clientSocket = new net.Socket();
      clientSocket.connect(addr, "127.0.0.1", () => {
        resolve({
          reader: clientSocket,
          writer: clientSocket,
        });
      });
    });
  };

  return new LanguageClient(language, serverOptions, getClientOptions());
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

export async function activate(context: ExtensionContext) {
  if (isStartedInDebugMode()) {
    // Development - Run the server manually
    client = startLangServerTCP(2087);
  } else {
    // Production - Client is going to run the server (for use within `.vsix` package)
    const cwd = path.join(__dirname, "../");
    const pythonPath = workspace.getConfiguration(language).get<string>("pythonPath");

    if (!pythonPath) {
      throw new Error(`${language}.pythonPath is not set`);
    }

    try {
      const { stdout } = await promisify(execFile)(pythonPath, ["-m", "pip", "show", "wdl-lsp"]).catch(err => {
        console.log(err);
        return { stdout: "" };
      });
      const versionStr = stdout.split('\n').find(line => line.startsWith('Version:'));
      if (!versionStr || versionStr.split(':')[1].trim() !== version) {
        await promisify(execFile)(pythonPath, [
          "-m", "pip", "install", "--user", "wdl-lsp==" + version,
        ]);
      }
    } catch (e) {
      console.error(e);
    }

    client = startLangServer(pythonPath, ["-m", "wdl_lsp"], cwd);
  }

  client.registerProposedFeatures();
  await client.start();
}

export function deactivate() {
  if (client) {
    return client.stop();
  }
}
