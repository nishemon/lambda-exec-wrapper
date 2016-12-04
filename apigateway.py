#coding:utf-8
import os
import json
import logging
import subprocess
import urllib
import time
import uhttplib
import collections
import re

import util

DEFAULT_FAKEROOT_LIB="/usr/lib64/fakechroot/libfakechroot.so"
DEFAULT_FAKEROOT_ROOT="/tmp/payload"
DEFAULT_FAKEROOT_BASE="./payload"

conf_fakeroot = collections.namedtuple('Fakeroot', ['preload', 'library_path', 'root', 'chroot', 'base'])
conf_connection = ""
conf_header = {}

logging.basicConfig(level=logging.INFO)
def _must_exists(path):
    return True

def _shouldnot_exists(path):
    return not os.path.exists(path)

def _makedirs(d):
    if _shouldnot_exists(d):
        os.makedirs(d)

def _force_makedirs(d):
    if not os.path.exists(d):
        os.makedirs(d)

def _rewrite_copy(src, dest, rules):
    matchers = []
    for pattern, replace in rules.items():
        matchers.append((re.compile(pattern), replace + "\n"))
    fr = open(src, 'r')
    _force_makedirs(os.path.dirname(dest))
    fw = open(dest, 'w')
    line = fr.readline()
    while line:
        for pattern, replace in matchers:
            line = pattern.sub(replace, line)
        fw.write(line)
        line = fr.readline()
    fr.close()
    fw.close()

def _symlinks(src, dest):
    if not os.path.exists(dest):
        os.symlink(src, dest)
        return
    #if not os.path.isdir(src) or not os.path.isdir(dest):
    for f in os.listdir(src):
        newSrc = os.path.join(src, f)
        newDest = os.path.join(dest, f)
        _symlinks(newSrc, newDest)

def _scan_symlink(src, dest, rewrite):
    if os.path.isdir(src):
        rewrited = set()
        for f in os.listdir(src):
            newSrc = os.path.join(src, f)
            newDest = os.path.join(dest, f)
            if _scan_symlink(newSrc, newDest, rewrite):
                rewrited.add(f)
        if rewrited:
            for f in os.listdir(src):
                if f in rewrited:
                    continue
                newSrc = os.path.join(src, f)
                newDest = os.path.join(dest, f)
                _symlinks(newSrc, newDest)
            return True
        return False
    rules = {}
    for regex, rule in rewrite.items():
        if re.search(regex, src):
            rules.update(rule)
    if rules:
        _rewrite_copy(src, dest, rules)
        return True
    return False

def _symlink(src, dest, rewrite = {}):
    if os.path.exists(dest):
        for f in os.listdir(src):
            newSrc = os.path.join(src, f)
            newDest = os.path.join(dest, f)
            _symlink(newSrc, newDest, rewrite)
    else:
        if not rewrite or not _scan_symlink(src, dest, rewrite):
            os.symlink(src, dest)

def cmd_mkdir(dirs):
	if isinstance(dirs, list):
		map(_makedirs, [conf_fakeroot.root + x for x in dirs])
	else:
		_makedirs(conf_fakeroot.root + dirs)

def cmd_fakechroot(params):
    global conf_fakeroot
    conf_fakeroot.root = os.path.abspath(params.get("root", DEFAULT_FAKEROOT_ROOT))
    conf_fakeroot.base = os.path.abspath(params.get("base", DEFAULT_FAKEROOT_BASE))
    lib = os.path.abspath(conf_fakeroot.base + params.get("lib", DEFAULT_FAKEROOT_LIB))
    
    _makedirs(conf_fakeroot.root)
    conf_fakeroot.library_path = os.path.dirname(lib)
    conf_fakeroot.preload = os.path.basename(lib)
    return setup_fakechroot

def setup_fakechroot(params):
    rewrite_rule = params.get("rewrite", {})
    symlinks = params.get("symlink", [])
    _symlink(conf_fakeroot.base, conf_fakeroot.root, rewrite_rule)
    if isinstance(symlinks, list):
        for src in symlinks:
            _symlink(os.path.abspath(src), conf_fakeroot.root + src)
    else:
        for src, to in symlinks.items():
            _symlink(os.path.abspath(src), conf_fakeroot.root + to)

def cmd_exec(option):
    return run_exec

def run_exec(option):
    if not isinstance(option, dict):
        binary = option
        setEnv = {}
        preset = False
    else:
	binary = option["bin"]
	setEnv = option.get("env", {})
        preset = option.get("preset", False)
    env = os.environ.copy()
    path = [x for x in [setEnv.get("LD_LIBRARY_PATH", None), env.get("LD_LIBRARY_PATH", None)] if x]
    if not preset:
	rpaths = util.getrpath(conf_fakeroot.root + binary, conf_fakeroot.root, path)
        path.extend([conf_fakeroot.root + x for x in rpaths])
    path.insert(0, conf_fakeroot.library_path)
    preload = [x for x in [conf_fakeroot.preload, setEnv.get("LD_PRELOAD", None), env.get("LD_PRELOAD", None)] if x]
    print path
    print preload
    env.update({
	"LD_LIBRARY_PATH": ":".join(path),
	"LD_PRELOAD": ":".join(preload)
    })
    if conf_fakeroot.library_path:
	argv = ["python", "mini_chroot.py", conf_fakeroot.root]
    else:
	argv = []
    if isinstance(binary, list):
	argv.extend(binary)
    else:
	argv.append(binary)
    proc = subprocess.Popen(argv, env = env)
    proc.communicate()

def cmd_connection(uri):
    global conf_connection
    if uri.startswith("unix:"):
        uri = "unix:" + conf_fakeroot.root + uri.replace("unix:", "", 1)
    conf_connection = uri

def cmd_logging(directive):
	return

def cmd_header(additional):
    global conf_header
    conf_header = additional

commands = [
  ('fakechroot',        cmd_fakechroot),
  ('mkdir',		cmd_mkdir),
  ('exec',		cmd_exec),
  ('connection',	cmd_connection),
  ('logging',		cmd_logging)
]

f = open("payload.json", 'r')
directive = json.loads("".join([x for x in f.readlines() if not x.lstrip().startswith("#")]))
f.close()

while commands:
    nextCommands = {}
    for cmd, dispatcher in commands:
        print cmd
        if cmd in directive:
            nextFunc = dispatcher(directive[cmd])
            if nextFunc:
                nextCommands[cmd] = nextFunc
    commands = nextCommands.items()

def lambda_handler(event, context):
    conn = uhttplib.UnixHTTPConnection(conf_connection)
    method = event.get("httpMethod", "GET")
    params = event.get("queryStringParameters", None)
    uri = event.get("path", "/") + (("?" + urllib.urlencode(params)) if params else "")
    headers = event.get("headers", {})
    headers.pop("Accept-Encoding", None)
    headers.update(conf_header)
    body = event.get("body", None)
    print uri
    conn.request(method, uri, body, headers)
    resp = conn.getresponse()
    respHeaders = dict(resp.getheaders())
    respHeaders.pop("connection", None)
    respHeaders.pop("transfer-encoding", None)
    respHeaders.pop("date", None)
    return {
	"statusCode": resp.status,
    	"body": resp.read(),
        #"headers": dict(resp.getheaders())
    }

