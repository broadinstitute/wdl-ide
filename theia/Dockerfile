FROM node:10-alpine AS base

ENV THEIA_DIR=/opt/theia

WORKDIR ${THEIA_DIR}



FROM base AS build

RUN apk add build-base python

ADD package.json ./

RUN yarn
RUN yarn theia build



FROM base

COPY --from=build ${THEIA_DIR} .

ENV USER=theia \
    THEIA_PLUGINS=local-dir:plugins,vscode:extension/broadinstitute.wdl

ADD settings.json /home/${USER}/.theia/

RUN apk add --no-cache docker git && \
    adduser -S ${USER} && \
    mkdir /home/${USER}/workspace && \
    chown -R ${USER} /home/${USER}

USER ${USER}

ENTRYPOINT ["yarn", "theia", "start", "/home/theia/workspace", "--hostname=0.0.0.0"]
