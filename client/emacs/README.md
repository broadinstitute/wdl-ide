## Installation

1. Install the `wdl-lsp` server:
```
$ pip3 install wdl-lsp
```

2. Install a WDL major mode in emacs. This is required to handle syntax highlighting and formatting. For example, [poly-wdl](https://github.com/jmonlong/poly-wdl) can be installed by typing
```
M-x package-install RET poly-wdl RET
```

3. Install [`eglot`](https://github.com/joaotavora/eglot)
```
M-x package-install RET eglot RET
```

4. Add the following lines to your Emacs config:
```
(require 'eglot)

(add-to-list 'eglot-server-programs '(wdl-mode . ("/usr/local/bin/wdl-lsp")))
(add-hook 'wdl-mode-hook 'eglot-ensure)
```

There are other LSP modes for emacs, such as [lsp-mode](https://github.com/emacs-lsp/lsp-mode). If you get them working, please add instructions to this README.
