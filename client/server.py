import subprocess, sys

def call(module, *args):
    python = sys.executable
    subprocess.check_call([python, '-m', module] + list(args))

try:
  import wdl_lsp
except ImportError:
  call('pip', 'install', 'wdl-lsp')

call('wdl_lsp')
