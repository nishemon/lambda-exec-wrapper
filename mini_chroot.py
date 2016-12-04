import os
import shlex
import subprocess
import sys

print "run mini_chroot"
sys.argv.pop(0)
root = os.path.abspath(sys.argv.pop(0))

argv = shlex.split(" ".join(sys.argv))

os.chdir(root)
os.chroot(root)

subprocess.call(argv)

