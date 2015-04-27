#!/usr/bin/env python

# Print a stack trace per thread for a running python process.
#
# WARNING WARNING WARNING WARNING WARNING WARNING WARNING WARNING WARNING
#
# This is risky and will have side effects on the victim process.
#
# This script uses gdb to dynamically call the C python API to inject and
# execute python code in the process then detaches from the hopefully still
# running python process.
#
# WARNING WARNING WARNING WARNING WARNING WARNING WARNING WARNING WARNING
#
#
# The injected code which is executed in __main__ is roughly:
#
#    imports sys
#    import traceback
#    __f = open('/tmp/stackdump_procid.txt', 'w+')
#    for thread, frame in sys._current_frames().items():
#        __f.write('Thread 0x%x:\n' % thread)
#        __f.write("".join(traceback.format_stack(frame)))
#        __f.write('\n')
#    __f.flush()
#    __f.close()
#
# The actual code injected is 4 oneliners with \n replaced with chr(0xA)
# It also isn't PEP8 etc
#
# No warranty, caveat emptor, don't run against a production python process etc
#
# References:
#  https://stripe.com/blog/exploring-python-using-gdb
#  https://code.google.com/p/modwsgi/wiki/DebuggingTechniques
#  https://github.com/lmacken/pyrasite
#
# Requirements:
#  - gdb
#  - a willing python process which uses the cython interpreter
#  - a stetson and cowboy boots (yehaaw!)
#

import sys
import os
import subprocess

# TODO XXX - argparse, check valid process, use tmpfile etc
processid = int(sys.argv[1])
dump_file = "/tmp/stackdump_%d.log" % processid
gdb_cmds_file = "/tmp/stackdump_%d_gdb.cmds" % processid

# gdb incantations
gdb_cmds = [
    'p PyGILState_Ensure()',
    'p PyRun_SimpleString("import sys; import traceback")',
    r"""p PyRun_SimpleString("__f = open('""" + dump_file + r"""', 'w+')")""",
    r"""p PyRun_SimpleString("for thread, frame in sys._current_frames().items(): __f.write('Thread 0x%x:' % thread); __f.write(chr(0xA)); __f.write(''.join(traceback.format_stack(frame))); __f.write(chr(0xA))")""",
    'p PyRun_SimpleString("__f.flush(); __f.close()")',
    'p PyGILState_Release($1)',
    'detach',
    'quit'
]

with open(gdb_cmds_file, 'w+') as f:
    f.write("\n".join(gdb_cmds))

# check_call ?
gdb = subprocess.Popen(['gdb', '-p', str(processid), '-x', gdb_cmds_file], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
output, errors = gdb.communicate()
if False:
    print output, errors


with open(dump_file) as infile:
    sys.stdout.write(infile.read())

os.remove(dump_file)
os.remove(gdb_cmds_file)
