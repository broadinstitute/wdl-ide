# VS Code IDE for WDL

This project aims to provide a "batteries-included" environment
for developing [WDL](http://www.openwdl.org/) workflows.

**Please note:** it is currently under active **development**,
and is not yet feature-complete.

## Debugger Extension

We will create an extension for [Visual Studio Code](https://code.visualstudio.com/) to
- [x] submit workflows for execution to a [Cromwell](https://cromwell.readthedocs.io) API
- [x] watch for completion/failure of each workflow (or cancel it)
- [ ] highlight task-specific failures
- [ ] provide feedback on runtime resource management

## Browser IDE

Additionally, we provide an Integrated Development Environment (IDE),
which runs in a web browser and is based on [Theia](https://www.theia-ide.org/).

It bundles WDL extensions for VS Code -
[Debugger](#debugger-extension) and
[Syntax Highlighter](https://marketplace.visualstudio.com/items?itemName=broadinstitute.wdl) -
along with a "local" instance of Cromwell.

The bundle consists of [Docker](https://www.docker.com/) containers,
which you can set up with a single
[Docker Compose](https://docs.docker.com/compose/) command.

This approach is used to
- develop workflows *locally*, with an ***ultra-fast*** feedback loop
- run workflows *in the cloud* from developer machine - no need for a Cromwell server
- create reproducible setup - it works on any OS with Docker Compose
- run the same setup on a remote server - think Notebooks, but for WDL!
- *simplify* local development - it just works&trade;

### Deployment

To deploy the IDE:
- clone or download this repo into a local folder
- install [Docker Compose](https://docs.docker.com/compose/install/)
- for *local-only* development, run this command in the cloned folder:
  ```
  docker compose up
  ```
- for local *and* Google cloud development, do the following instead [*]:
  - [create a project](https://cloud.google.com/resource-manager/docs/creating-managing-projects#creating_a_project) on [Google Cloud Platform](https://cloud.google.com/)
  - [create a service account](https://cloud.google.com/iam/docs/creating-managing-service-accounts#creating_a_service_account) with project-wide `Genomics Pipelines Runner` _role_, and **download** its key in JSON format
  - [grant](https://cloud.google.com/iam/docs/granting-roles-to-service-accounts#granting_access_to_a_user_for_a_service_account) it `Service Account User` _permission_ **on**
      `Compute Engine default service account` in that project
  - [create](https://cloud.google.com/storage/docs/creating-buckets) a bucket for Cromwell executions
  - [grant](https://cloud.google.com/storage/docs/access-control/using-iam-permissions#bucket-add) `Storage Object Admin` _permission_ on the Cromwell executions bucket
  - run this command, replacing `<...>` with your values:
    ```
    GOOGLE_APPLICATION_CREDENTIALS=./<your-service-account-key>.json \
    GOOGLE_AUTH_MODE=service-account \
    GOOGLE_CLOUD_PROJECT=<your-project-name> \
    GOOGLE_EXECUTIONS_BUCKET=<executions-bucket-name> \
    docker-compose up
    ```
  [*] In the future, we may provide a simplified script to do most of the above.

The first time you run the Docker compose command, it will take ~5 minutes to compile the IDE from sources and bring up the environment. Later on, we will provide a Docker image to speed that up.

When you no longer see the log messages, the IDE is running and you can navigate
to it in a browser at this address: [localhost:3000](http://localhost:3000).

## License

This project is **not yet licensed** for external use.

However, we anticipate a BSD-type license could be obtained
in the near future.
