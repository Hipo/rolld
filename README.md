
gracefully restarting is a delicate business, rolld tries to help restarting your processes without losing a single request.


What
--------
rolld is a simple process supervisor, that manages and restarts your processes.

How
--------

There are different tactics when restarting a process group. rolld does the following,

i. start a new set of processes in different ports
ii. run some smoke tests - eg. send request to each port.
iii. update your loadbalancers config, reload your loadbalancer
iv. wait until there is no connection on the old set of processes
v. kill old ones.

rolld uses a simple yml file for configuration

```
app-servers:
  cmd: '../env/bin/python app.py {numproc}'
  directory: '/Users/aybarsbadur/projects/rolld/example'
  stderr: 'logs/tornado-{numproc}.err'
  stdout: 'logs/tornado-{numproc}.log'

  workset:
    - numprocs: [8001, 8002, 8003, 8004]
    - numprocs: [8501, 8502, 8503, 8504]

  smoke_test:
    - check_all_http_ports: numprocs

  after_start:
    - replace_file: [numprocs, 'example/nginx-tornado.conf.templ', 'example/nginx-tornado.conf']
    - run_proc: ps auxw| grep nginx | grep master | grep -v grep | awk '{print $2}' | xargs kill -HUP
```

then you can run rolld

```
rolld rolld.yml
```

when you want to restart your processes send a HUP signal to rolld

```
killall -HUP rolld
```

or

```
ps auxw | grep rolld | grep -v grep | awk '{print $2}' | xargs kill -HUP
```


When
---------

Always refer to your fav. application server (uwsgi, gunicorn, passenger etc.) they may have graceful restart built-in.

Also after configuring your app server, you can easily check if it does graceful loading like this

open a terminal and run curl every second, eg.

```
while curl --fail -s localhost:80 > /dev/null; do echo "passed"; sleep 1; done;
```

and then reload/restart your app. If it doesn't exit, then you are fine, else you might have a mis-configuration,
or you might need rolld.



