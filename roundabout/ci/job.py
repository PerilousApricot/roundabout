""" Roundabout CI job module. """

import time
import urllib2
import types

from roundabout import log


JOB_CLASSES = {}


class JobException(Exception):
    """A Job Exception."""
    pass


def get_ci_class(name):
    """CI class factory."""
    try:
        return JOB_CLASSES[name]
    except KeyError:
        raise JobException("No class registered to handle %s" % name)


class Job(object):
    """ A Hudson Job is a configuration for CI builds. """

    def __init__(self, config, opener=None):
        self.config = config
        self.opener = opener or urllib2.urlopen  # Use a test opener or urllib2

    def __nonzero__(self):
        raise NotImplementedError("Descendent classes should implement this")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def reload(self):
        """Sleep for configured time, the descendent class should then reload
        the data for the job.
        """
        sleeptime = int(self.config["ci"].get("job_reload_sleep", 30))
        log.info("Job not complete, sleeping for %s seconds..." % sleeptime)
        time.sleep(sleeptime)

    @property
    def url(self):
        """The Job url is the human-readable reference for the log or
        pull-request."""
        raise NotImplementedError("Descendent classes should implement this")

    @property
    def complete(self):
        """Whether or not the job is complete."""
        raise NotImplementedError("Descendent classes should implement this")

    @classmethod
    def spawn(cls, branch, config, build_name=None, opener=None):
        """
        Create and return a paramaterized Job based on the CI config.
        """
        if build_name == None:
            # to support unittests
            # TODO: remove this and then fix the tests
            if isinstance( config["ci"]["job"], types.StringTypes ):
                build_name = config["ci"]["job"]
            else:
                build_name = config["ci"]["job"][0]
                
        ci_class = get_ci_class(config["ci"]["class"])
        log.info("Starting %s job" % config["ci"]["class"])

        return ci_class.spawn(branch, config, build_name, opener)

    @classmethod
    def register(cls, name, job_class):
        """Register a CI class."""
        if not issubclass(job_class, cls):
            raise JobException("Cannot register %s, not a Job" % job_class)

        JOB_CLASSES[name] = job_class
