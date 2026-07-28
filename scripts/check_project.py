import compileall
import re

ignored = re.compile(r"/(\.git|\.venv|staticfiles|media)/")
ok = compileall.compile_dir(".", quiet=1, rx=ignored)
raise SystemExit(0 if ok else 1)
