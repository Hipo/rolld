import subprocess
import tornado
from tornado.ioloop import IOLoop
from tornado.process import Subprocess
import shlex
from functools import partial
import os
import requests
from tornado.ioloop import PeriodicCallback
import sys
import signal
import time
import logging

def exit_callback(*args, **kwargs):
    print args, kwargs

def out_fn(line, name=None):
    print "name >>>", line

def periodic_callback(proc_pid):
    global rolld_proc, nginx_proc
    try:
        r = requests.get('http://localhost:9091')
        print "checking", r.status_code
        assert r.status_code == 200
    except:
        logging.exception("periodic callback")
        periodic_checker.stop()

        os.kill(rolld_proc.pid, signal.SIGTERM)
        os.kill(nginx_proc.pid, signal.SIGTERM)

        IOLoop.instance().add_timeout(time.time() + 5, partial(sys.exit, 1))


periodic_checker = None
rolld_proc = None
nginx_proc = None


def exit_test():
    global periodic_checker
    if periodic_checker:
        periodic_checker.stop()
    os.kill(rolld_proc.pid, signal.SIGTERM)
    os.kill(nginx_proc.pid, signal.SIGTERM)
    # IOLoop.instance().add_timeout(time.time() + 5, partial(sys.exit, 0))
    # check if we have zombies left
    try:
        lines = subprocess.check_output('ps auxw | grep python | grep app.py | grep -v grep', shell=True)
        print lines
        assert len(lines) == 0
    except subprocess.CalledProcessError as grepexc:
        # grep shouldnt find anything so exit code should be 1
        if grepexc.returncode == 1:
            pass
        else:
            raise
    # if everything is fine, just stop our ioloop now.
    IOLoop.current().stop()

def main():
    global rolld_proc, nginx_proc
    # start rolld
    rolld_proc = Subprocess(
        shlex.split("rolld example/rolld.yaml"),
        stdout=Subprocess.STREAM,
        stderr=Subprocess.STREAM,
    )
    out = partial(out_fn, name='rolld')
    rolld_proc.stdout.read_until_close(exit_callback, streaming_callback=out)
    rolld_proc.stderr.read_until_close(exit_callback, streaming_callback=out)

    # start nginx on port 9091
    nginx_proc = Subprocess(
        shlex.split("""nginx -p "%s" -c example/nginx.conf""" % os.path.curdir),
        stdout=Subprocess.STREAM,
        stderr=Subprocess.STREAM,
    )
    out = partial(out_fn, name='rolld')
    nginx_proc.stdout.read_until_close(exit_callback, streaming_callback=out)
    nginx_proc.stderr.read_until_close(exit_callback, streaming_callback=out)


    # now we restart everything
    def send_hub_to_rolld():
        print "sending SIGHUP to rolld"
        os.kill(rolld_proc.pid, signal.SIGHUP)

    def start_ping():
        global periodic_checker
        periodic_checker = PeriodicCallback(partial(periodic_callback, proc_pid=rolld_proc.pid), 1000)
        periodic_checker.start()

    IOLoop.instance().add_timeout(time.time() + 5, start_ping)
    IOLoop.instance().add_timeout(time.time() + 15, send_hub_to_rolld)
    IOLoop.instance().add_timeout(time.time() + 55, exit_test)




if __name__ == '__main__':
    ioloop = IOLoop.instance()
    ioloop.add_callback(main)
    ioloop.start()
