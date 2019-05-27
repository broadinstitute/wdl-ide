FROM node:10-alpine AS base

ENV THEIA_DIR=/opt/theia

WORKDIR ${THEIA_DIR}


FROM base AS build

RUN apk add build-base python

ADD package.json ./

RUN yarn
RUN yarn theia build

WORKDIR ${THEIA_DIR}/plugins

RUN download() { \
      wget -O $1.$2-$3.vsix \
        https://ms-vscode.gallery.vsassets.io/_apis/public/gallery/publisher/$1/extension/$2/$3/assetbyname/Microsoft.VisualStudio.Services.VSIXPackage ; \
    } && \
    download broadinstitute wdl 1.0.0



FROM base

COPY --from=build ${THEIA_DIR} .

ENV USER=theia \
    WORKSPACE=/home/workspace

ADD settings.json ${WORKSPACE}/.theia/

RUN apk add --no-cache curl git && \
    adduser -Sh ${WORKSPACE} ${USER} && \
    chown -R ${USER} ${WORKSPACE} && \
    chmod +w .

USER ${USER}

ENTRYPOINT ["yarn", "theia", "start", "/home/workspace", "--hostname=0.0.0.0", "--plugins=local-dir:plugins"]
