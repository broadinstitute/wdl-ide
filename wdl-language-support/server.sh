#!/bin/sh

export PYTHONPATH=$(dirname "$0")
PATH=$PATH:/usr/local/bin

$(which python3) -m server
