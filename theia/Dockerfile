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
    WORKSPACE=/home/workspace \
    THEIA_PLUGINS=local-dir:plugins,vscode:extension/broadinstitute.wdl

ADD settings.json ${WORKSPACE}/.theia/

RUN apk add --no-cache curl docker git && \
    adduser -Sh ${WORKSPACE} ${USER} && \
    chown -R ${USER} ${WORKSPACE} && \
    chmod +w .

USER ${USER}

ENTRYPOINT ["yarn", "theia", "start", "/home/workspace", "--hostname=0.0.0.0"]
