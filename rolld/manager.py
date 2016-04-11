from tornado.process import Subprocess
from tornado.ioloop import IOLoop
from tornado.gen import Task, Return, coroutine
import shlex
import psutil
import time
from tornado.ioloop import PeriodicCallback
from tornado import gen
import logging
import requests
import subprocess
from functools import partial
import yaml
import sys
import os.path
import os

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def exit_callback(*args, **kwargs):
    print ">>> exiting >>>", args, kwargs

def _out(line, filehandler=None, head=""):
    if head:
        line = "%s%s" % (head, line)
    filehandler.write(line)
    filehandler.flush()

def get_out_file_name(directory, fname):
    if fname.startswith(directory):
        return fname
    return os.path.join(directory, fname)

def run_proc(port, cmd, stdout_file, stderr_file, directory):
    run_cmd = cmd.format(numproc=port)

    if directory.startswith('.'):
        directory = os.path.realpath(directory)
        print "Directory", directory

    if not os.path.exists(directory):
        raise Exception('working directory doesnt exist')

    proc = Subprocess(
        shlex.split(run_cmd),
        stdout=Subprocess.STREAM,
        stderr=Subprocess.STREAM,
        cwd=directory
    )
    proc.set_exit_callback(exit_callback)

    std_out_log_file_name = get_out_file_name(directory, stdout_file.format(numproc=port))
    std_err_log_file_name = get_out_file_name(directory, stderr_file.format(numproc=port))
    stdout_fhandler = open(std_out_log_file_name, 'a')
    stderr_fhandler = open(std_err_log_file_name, 'a')
    out_fn = partial(_out, filehandler=stdout_fhandler, head="%s: " % port)
    err_fn = partial(_out, filehandler=stderr_fhandler, head="%s: " % port)

    proc.stdout.read_until_close(exit_callback, streaming_callback=out_fn)
    proc.stderr.read_until_close(exit_callback, streaming_callback=err_fn)

    return proc

# this is global, yes
processes = []
restart_counter = 0
state = 'IDLE'

# def periodic_callback():
#     for i in processes:
#         proc = psutil.Process(i.pid)
#         conns = proc.connections()
#
#         # find our listening port
#         ports = set()
#         for conn in conns:
#             if conn.status == 'LISTEN':
#                 if conn.laddr:
#                     ports.add(conn.laddr[1])
#
#         for conn in conns:
#             if conn.status == 'ESTABLISHED' and conn.laddr[1] in ports:
#                 print "conn ", conn
#         print ">>>>", i.pid

class Actions(object):

    @classmethod
    def check_all_http_ports(cls, ports, path='/'):
        """
        sends a get request to given ports
        :param ports:
        :return:
        """
        # do some smoke test
        for port in ports:
            logger.info('checking with - %s', port)
            r = requests.get('http://localhost:%s/' % port, timeout=5.0)
            if r.status_code == 200:
                logger.info('passed - %s' % port)
            else:
                # we failed to start, now cleanup
                logger.fatal('failed to start - %s' % port)
                # TODO: do cleanup

    @classmethod
    def replace_file(cls, ports, infile, outfile):
        from jinja2 import Template
        t = Template(open(infile, 'r').read())
        out = t.render(ports=ports)
        with open(outfile, 'w') as f:
            f.write(out)

    @classmethod
    def run_proc(cls, cmd):
        logger.info("running cmd: %s", cmd)
        subprocess.check_call(cmd, shell=True)

def get_config():
    if not len(sys.argv) > 1:
        raise Exception('please give config file path')
    if not os.path.exists(sys.argv[1]):
        raise Exception("config file doesn't exists")
    stream = open(sys.argv[1], "r")
    docs = yaml.load_all(stream)
    for f in docs:
        return f

def start_processes(config, workset):
    process_set = []
    for port in workset['numprocs']:
        logger.info('starting port - %s', port)
        p = run_proc(port,
                     cmd=config['cmd'],
                     stdout_file=config['stdout'],
                     stderr_file=config['stderr'],
                     directory=config['directory'])
        process_set.append(p)
    return process_set

def has_connection(processes):
    for i in processes:
        proc = psutil.Process(i.pid)
        conns = proc.connections()

        # find our listening port
        ports = set()
        for conn in conns:
            if conn.status == 'LISTEN':
                if conn.laddr:
                    ports.add(conn.laddr[1])

        for conn in conns:
            if conn.status == 'ESTABLISHED' and conn.laddr[1] in ports:
                print "conn ", conn
                return True


def run_actions(conf_item, workset):
    for i in conf_item:
        for k, v in i.items():
            fn = getattr(Actions, k)
            args = []
            if not isinstance(v, list):
                v = [v]

            for arg in v:
                if arg == 'numprocs':
                    args.append(workset['numprocs'])
                else:
                    args.append(arg)
            fn(*args)


@coroutine
def restart_all():
    global state, processes, restart_counter

    config = get_config()
    config = config['app-servers']

    workset = config['workset'][restart_counter % len(config['workset'])]

    try:

        if state != 'IDLE':
            return

        state = 'RESTARTING'
        process_set = start_processes(
                config=config,
                workset=workset,
        )

        # wait for 5 seconds
        logger.info('waiting for 5 seconds')
        yield gen.Task(IOLoop.instance().add_timeout, time.time() + 5)

        run_actions(config['smoke_test'], workset)
        run_actions(config['after_start'], workset)


        logger.info("waiting connections on processes")
        while True:
            if not has_connection(processes):
                break
            logger.info("waiting connections on processes")
            yield gen.Task(IOLoop.instance().add_timeout, time.time() + 1)

        for i in processes:
            try:
                os.kill(i.pid, signal.SIGTERM)
            except:
                logger.exception("couldnt kill process")

        logger.info("killed old ones")
        processes = process_set
        restart_counter += 1
        state = 'IDLE'

    except:
        logger.exception("restart got an exception")

import signal, os
def handler(signum, frame):
    print 'Signal handler called with signal', signum
    ioloop.add_timeout(time.time() + 1, restart_all)

signal.signal(signal.SIGHUP, handler)

import atexit

@atexit.register
def at_exit():
    """
    ensure we dont have any child left around
    """
    global processes
    for i in processes:
        proc = psutil.Process(i.pid)
        print "killing proc", proc, i.pid
        proc.kill()

def term_handler(signum, frame):
    at_exit()
    sys.exit(0)

signal.signal(signal.SIGTERM, term_handler)
signal.signal(signal.SIGINT, term_handler)


def main():
    if not len(sys.argv) > 1:
        print "config file not set"
        print "usage: \nrolld config.yml\n"
        return

    global processes, ioloop
    ioloop = IOLoop.instance()
    ioloop.add_callback(restart_all)
    # pc = PeriodicCallback(periodic_callback, 1000)
    # pc.start()
    ioloop.start()


if __name__ == "__main__":
    main()