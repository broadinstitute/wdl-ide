# VS Code IDE for WDL

This project aims to provide a "batteries-included" environment
for developing [WDL](http://www.openwdl.org/) workflows.

**Please note:** it is currently under active **development**,
and is not yet feature-complete.

## Debugger Extension

We will create an extension for [Visual Studio Code](https://code.visualstudio.com/) to
- submit workflows for execution to a [Cromwell](https://cromwell.readthedocs.io) API
- watch for completion/failure of each workflow
- highlight task-specific failures
- provide feedback on runtime resource management

## Cloud IDE

Additionally, we will provide a cloud-ready IDE,
which is based on [Theia](https://www.theia-ide.org/).

It bundles WDL extensions for VS Code -
[Debugger](#debugger-extension) and
[Syntax Highlighter](https://marketplace.visualstudio.com/items?itemName=broadinstitute.wdl) -
along with a "local" instance of Cromwell.

This bundle runs in [Docker](https://www.docker.com/) containers,
and is set up with a single
[Docker Compose](https://docs.docker.com/compose/) command.

The approach is used to
- develop workflows *locally*, with an ***ultra-fast*** feedback loop
- run workflows *in the cloud* from developer machine - no need for a Cromwell server
- create reproducible setup - it works on any OS with Docker Compose
- run the same setup on a remote server - think Notebooks, but for WDL!
- *simplify* local development - it just works&trade;

## License

This project is **not yet licensed** for external use.

However, we anticipate a BSD-type license could be obtained
in the near future.
