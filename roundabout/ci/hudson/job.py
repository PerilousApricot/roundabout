""" Roundabout hudson/jenkins module. """

import json
import base64
import time
import urllib2
import types

from roundabout import log
from roundabout.ci import job
from roundabout.ci.hudson import build


class Job(job.Job):
    """ A Hudson Job is a configuration for CI builds. """
    def __init__(self, config, opener=None):
        super(Job, self).__init__(config, opener)

        self.build = {}
        self.job_endpoint = "%s/job/%s/api/json?depth=1" % (
                                    config["ci"]["base_url"],
                                    "%s")
        self.build_endpoint = "%s/job/%s/buildWithParameters?branch=%s"
        self._job_list = []

    def __nonzero__(self):
        return bool(self.build)

    @classmethod
    def spawn(cls, branch, config, opener=None):
        """
        Create and return a paramaterized build of the current job
        """

        _job = cls(config, opener=opener)

        if isinstance( _job.config["ci"]["job"], types.StringTypes ):
            _job._job_list = [_job.config["ci"]["job"]]
        else:
            _job._job_list = _job.config["ci"]["job"]
        
        for current_job in _job._job_list:
            log.info("Starting: %s for %s" % (current_job, branch))
            build_retval = _job.req(_job.build_endpoint % (_job.config["ci"]["base_url"],
                                               current_job, branch))
            if build_retval:
                build_id = _job.properties[current_job]['nextBuildNumber']
                while True:
                    # Keep trying until we return something.
                    try:
                        _job.build[current_job] = [b for b
                                        in _job.builds[current_job]
                                        if build_id == b.number][0]
                        log.info( "build is %s " % _job.build )
#                        log.info("Build URL: %s" % _job.url[current_job])
                        return _job
                    except IndexError:
                        time.sleep(1)

    @property
    def job_list(self):
        return self._job_list

    @property
    def builds(self):
        """ Return the list of builds for this job. """
        return dict((job_name, 
                    [build.Build(self, b) for b in self.properties[job_name]['builds']]) 
                    for job_name in self.job_list )

    @property
    def properties(self):
        """ Return the JSON decoded properties for these jobs. """
        return dict( (job_name, self.req(self.job_endpoint % job_name, json_decode = True ) )
                     for job_name in self.job_list )

    @property
    def url(self):
        """ Return the URLs of our builds """
        print "builds are %s" % self.build
        retval =  dict( (job_name, self.build[job_name].url )
                     for job_name in self.job_list )
        print "retval is %s" % retval
        return retval

    @property
    def complete(self):
        """ Return true if the build is complete """
        for one_build in self.build.values():
            log.debug( "one build is %s" % one_build )
            if not one_build.complete:
                return False
        return True

    def reload(self):
        """ call ci.job.Job.reload to sleep, then reload the build."""
        super(Job, self).reload()
        return dict( (job_name, self.build[job_name].reload())
                     for job_name in self.job_list )

    def req(self, url, json_decode=False):
         """
         Connect to remote url, using the provided credentials. Return either
         the result or if json_decode=True, the JSONDecoded result.
         """
         username = self.config["ci"]["username"]
         password = self.config["ci"]["password"]
         b64string = base64.encodestring("%s:%s" % (username, password))[:-1]
         req = urllib2.Request(url)
         if "http_proxy" in self.config["ci"]:
            req.set_proxy( self.config["ci"]["http_proxy"], 
                           self.config["ci"]["http_proxy_type"] )
         req.add_header("Authorization", "Basic %s" % b64string)
 
         try:
             res = self.opener(req)
         except Exception as e:
             contents = e.read()
             log.error(contents) # http errors have content bodies... like servlet
                                # container stacktraces. I'm looking at you, 
                                # Jenkins... -grue
             raise e

         if json_decode:
             res = json.loads(res.read())

         return res


job.Job.register('hudson', Job)
job.Job.register('jenkins', Job)

