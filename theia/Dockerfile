FROM node:10-alpine AS base

ENV THEIA_DIR=/opt/theia

WORKDIR ${THEIA_DIR}



FROM base AS build

RUN apk add --no-cache \
      build-base \
      git \
      libsecret-dev \
      patch \
      python

ADD package.json plugin-ext.patch ./

RUN yarn
RUN patch -p0 -N < plugin-ext.patch
RUN yarn theia build

RUN yarn global add vsce
RUN mkdir plugins

RUN git clone --depth 1 https://github.com/microsoft/vscode /vscode && \
    cd /vscode/extensions/docker && \
    yes | vsce package && \
    cp *.vsix ${THEIA_DIR}/plugins/



FROM base

COPY --from=build ${THEIA_DIR} .

ENV USER=theia \
    THEIA_PLUGINS=local-dir:plugins,vscode:extension/broadinstitute.wdl,vscode:extension/PeterJausovec.vscode-docker

ADD settings.json /home/${USER}/.theia/

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
