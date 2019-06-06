#!/bin/sh

export PYTHONPATH=$(dirname "$0")
PATH=$PATH:/usr/local/bin

exec $(which python3) -m server
