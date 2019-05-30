## -------------------------
## Base image for all builds

FROM node:10-alpine AS base

ENV THEIA_DIR=/opt/theia

WORKDIR ${THEIA_DIR}

## ----------------------------
## Build all packages for Theia

FROM base AS build

RUN apk add --no-cache \
      build-base \
      git \
      libsecret-dev \
      patch \
      python

ADD theia/package.json theia/plugin-ext.patch ./

# build Theia

RUN yarn
RUN patch -p0 -N < plugin-ext.patch

RUN yarn theia build
RUN mkdir plugins

# helper script for VSCode plugin packaging

RUN yarn global add vsce
ADD scripts/vsce-package.sh /tmp/

# Docker syntax highlighter plugin

RUN git clone --depth 1 https://github.com/microsoft/vscode /vscode

WORKDIR /vscode/extensions/docker

RUN /tmp/vsce-package.sh

# WDL Debugger plugin

WORKDIR /tmp/wdl-debugger

ADD wdl-debugger/package.json .
RUN yarn

ADD wdl-debugger/ .
RUN /tmp/vsce-package.sh

## ----------------------------------
## Copy packages into the final image

FROM base

COPY --from=build ${THEIA_DIR} .

ENV USER=theia \
    THEIA_PLUGINS=local-dir:plugins,vscode:extension/broadinstitute.wdl,vscode:extension/PeterJausovec.vscode-docker

ADD theia/settings.json /home/${USER}/.theia/

RUN apk add --no-cache \
      docker \
      git \
      libsecret \
    && \
    adduser -S ${USER} && \
    mkdir /home/${USER}/workspace && \
    chown -R ${USER} /home/${USER}

USER ${USER}

ENTRYPOINT ["yarn", "theia", "start", "/home/theia/workspace", "--hostname=0.0.0.0"]
