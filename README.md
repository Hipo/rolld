rolld
=====

Gracefully restarting processes is a delicate business. `rolld` helps you restart any group of processes without losing a single request. This is especially useful during no-downtime deployments and in continuous integration implementations.


How Does It Work?
-----------------

There are different tactics when restarting a process group. `rolld` does the following:

* Starts a new set of processes in different ports
* Runs smoke tests (eg. send predefined requests to each port)
* Updates your load balancer configuration and reloads it
* Waits until there is no connection on the old set of processes
* Kills old processes

`rolld` uses a simple yml file for configuration:

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

Then you can run `rolld` like this:

    rolld rolld.yml

When you want to restart your processes send a HUP signal to `rolld`

    killall -HUP rolld

or

    ps auxw | grep rolld | grep -v grep | awk '{print $2}' | xargs kill -HUP


Who Should Use This?
--------------------

Always refer to your application server documentation first (uwsgi, gunicorn, passenger etc.) they may have graceful restart built-in already.

If you are not sure if you need `rolld`, there is an easy way to figure it out. You can easily check if your application server does graceful loading by running `curl` every second:

    while curl --fail -s localhost:80 > /dev/null; do echo "passed"; sleep 1; done;

And then reload/restart your application server. If it doesn't exit, then you are fine, else you need a solution like `rolld` to handle it for you.


Credits
-------

`rolld` is brought to you by 
[Aybars Badur](https://github.com/ybrs) and the [Hipo Team](http://hipolabs.com).


License
-------

`rolld` is licensed under the terms of the Apache License, version 2.0. Please see the LICENSE file for full details.
