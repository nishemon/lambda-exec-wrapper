import os
import shlex
import subprocess
import sys

loaded = set()
# not real rule, but LD_PRELOAD limit
def getlibsrpath(fakeroot, findpaths, libs, librarypath):
    rpaths = []
    for lib in libs:
        if lib in loaded:
            break
        for d in librarypath:
            f = os.path.join(d, lib)
            if os.path.exists(f):
                rpaths.extend(getrpath(f, fakeroot, librarypath))
                loaded.add(lib)
        for d in findpaths:
            f = fakeroot + os.path.join(d, lib)
            if os.path.exists(f):
                rpaths.extend(getrpath(f, fakeroot, librarypath))
                loaded.add(lib)
                break
    return rpaths

def getrpath(elf, fakeroot, librarypath):
    dynsec = subprocess.check_output(["readelf", "-d", elf])
    libs = []
    rpath = None
    for line in dynsec.split('\n'):
        line = line.strip()
        if line.startswith('0x0000000000000001'):
            libs.append(line.partition(':')[2].strip(' []'))
        elif line.startswith('0x000000000000000f'):
            rpath = line.partition(':')[2].strip(' []').split(':')
    if rpath:
        rpath.extend(getlibsrpath(fakeroot, rpath, libs, librarypath))
        return rpath
    return []

