""" Roundabout is a tarmac style merge bot for github """

import sys
import time

import roundabout.config
import roundabout.daemon
import roundabout.github.client

from roundabout import log
from roundabout import git_client
from roundabout import pylint
from roundabout import ci
from roundabout.loop import RoundaboutLoop

def main(command, options):
    """ Function called by bin/roundabout """

    config_file = options.config_file or roundabout.config.DEFAULT
    config = roundabout.config.Config(config_file)
    if command == "run":
        log.init_logger(config, stream=True)
    else:
        log.init_logger(config)

        daemon = roundabout.daemon.Daemon(
                    stdin="roundabout.log",
                    stdout="roundabout.log",
                    stderr="roundabout.log",
                    pidfile=config["default"].get("pidfile", "roundabout.pid"))

        if command == "start":
            daemon.start()
        elif command == "stop":
            daemon.stop()
            sys.exit(0)
        elif command == "restart":
            daemon.restart()

    try:
        run(config)
    except KeyboardInterrupt:
        pass
    except Exception, e:
        log.error("Unknown error: %s" % str(e))
    finally:
        sys.exit(0)

def run(config):
    """
    Run roundabout forever or until you kill it.
    """
    loop_handler     = RoundaboutLoop()
    wake_time        = time.time()
    github_wait_time = 0
    ci_wait_time     = 0
    while True:
        if wake_time > time.time():
            log.info("No work to do, Sleeping")
            time.sleep( wake_time - time.time())
            
        github = roundabout.github.client.Client(config)
        loop_handler.init_loop( github, config )
        
        # Process requests, possibly enqueueing new jobs
        if time.time() > github_wait_time:
            github_wait_time = loop_handler.process_requests()
        
        # Submit new jobs to the CI for processing
        loop_handler.submit_jobs()
        
        # Check status of running jobs, update github if necessary
        if time.time() > ci_wait_time or github_wait_time == 0:
            ci_wait_time = loop_handler.query_jobs()
        
        wake_time = min( ci_wait_time, github_wait_time )
