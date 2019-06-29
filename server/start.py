import subprocess, sys

def call(module, *args):
    python = sys.executable
    subprocess.check_call([python, '-m', module] + list(args))

call('pip', 'install', 'wdl-lsp')
call('wdl-lsp')
