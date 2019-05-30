#!/bin/sh

vsce package --yarn
cp *.vsix ${THEIA_DIR}/plugins/
