import runpy
import shutil
import sys

sys.argv = ['parsnips']
cli_path = shutil.which('parsnips')
if not cli_path:
    raise RuntimeError("Could not find 'parsnips' in PATH.")
runpy.run_path(cli_path, run_name="__main__")
