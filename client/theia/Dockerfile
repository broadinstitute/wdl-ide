## -------------------------
## Base image for all builds

FROM alpine AS base

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
      python \
      yarn

ADD client/theia/package.json client/theia/plugin-ext.patch ./

# build Theia

RUN yarn global add node-gyp

RUN yarn
RUN patch -p0 -N < plugin-ext.patch

RUN export NODE_OPTIONS=--max_old_space_size=2048 && \
    yarn theia build

RUN mkdir plugins

# helper script for VSCode plugin packaging

RUN yarn global add vsce
ADD scripts/vsce-package.sh /tmp/

# Docker syntax highlighter plugin

RUN git clone --depth 1 https://github.com/microsoft/vscode /vscode

WORKDIR /vscode/extensions/docker

RUN /tmp/vsce-package.sh

## ----------------------------------
## Copy packages into the final image

FROM base

ENV USER=theia \
    THEIA_PLUGINS=local-dir:plugins,vscode:extension/broadinstitute.wdl-devtools
    # vscode:extension/PeterJausovec.vscode-docker

RUN apk add --no-cache \
      docker \
      git \
      libsecret \
      python3 \
      yarn \
    && \
    adduser -S ${USER} && \
    mkdir /home/${USER}/workspace

COPY --from=koalaman/shellcheck-alpine /bin/shellcheck /usr/local/bin/
COPY --from=build ${THEIA_DIR} .

USER ${USER}

ADD client/theia/settings.json /home/${USER}/.theia/

ENTRYPOINT ["yarn", "theia", "start", "/home/theia/workspace", "--hostname=0.0.0.0"]
