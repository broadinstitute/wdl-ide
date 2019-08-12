## Installation

First, please install `wdl-lsp` server:
```
pip3 install wdl-lsp
```

Then, install `eglot` and add the following lines to Emacs config:
```
(require 'eglot)

(add-to-list 'eglot-server-programs '(wdl-mode . ("/usr/local/bin/wdl-lsp")))
```
