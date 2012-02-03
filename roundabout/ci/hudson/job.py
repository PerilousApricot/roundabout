""" Roundabout hudson/jenkins module. """

import json
import base64
import time
import urllib2
import httplib
import types

from roundabout import log
from roundabout.ci import job
from roundabout.ci.hudson import build


class Job(job.Job):
    """ A Hudson Job is a configuration for CI builds. """
    def __init__(self, config, build_name, opener=None):
        super(Job, self).__init__(config, opener)

        self.build = {}
        self.job_endpoint = "%s/job/%s/api/json?depth=1" % (
                                    config["ci"]["base_url"],
                                    "%s")
        self.build_endpoint = "%s/job/%s/buildWithParameters?branch=%s"
        self.build_name = build_name

    def __nonzero__(self):
        return bool(self.build)

    @classmethod
    def spawn(cls, branch, config, build_name, opener=None):
        """
        Create and return a paramaterized build of the current job
        """

        _job = cls(config, build_name = build_name, opener=opener)
        log.info("Building: %s for %s" % (build_name, branch))
        print ("building: %s for %s" % (build_name, branch))
        if _job.req(_job.build_endpoint % (_job.config["ci"]["base_url"],
                                          build_name, branch)):
            build_id = _job.properties['nextBuildNumber']
            while True:
                print "spin"
                # Keep trying until we return something.
                try:
                    _job.build = [b for b
                                    in _job.builds
                                    if build_id == b.number][0]
                    log.info("Build URL: %s" % _job.url)
                    return _job
                except IndexError:
                    time.sleep(1)
                    
    @property
    def builds(self):
        """ Return the list of builds for this job. """
        return [build.Build(self, b) for b in self.properties['builds']]

    @property
    def properties(self):
        """ Return the JSON decoded properties for this job. """
        return self.req(self.job_endpoint % self.build_name, json_decode=True)

    @property
    def url(self):
        """ Return the URL of our build """
        return self.build.url

    @property
    def complete(self):
        """ Return true if the build is complete """
        return self.build.complete

    def reload(self):
        """ call ci.job.Job.reload to sleep, then reload the build."""
        super(Job, self).reload()
        return self.build.reload()

    def req(self, url, json_decode=False):
        """
        Connect to remote url, using the provided credentials. Return either
        the result or if json_decode=True, the JSONDecoded result.
        """
        username = self.config["ci"]["username"]
        password = self.config["ci"]["password"]
        b64string = base64.encodestring("%s:%s" % (username, password))[:-1]
        req = urllib2.Request(url)
        print "header is %s" % b64string
        req.add_header("Authorization", "Basic %s" % b64string)  
        if "http_proxy" in self.config["ci"]:    
            req.set_proxy( self.config["ci"]["http_proxy"],
                           self.config["ci"]["http_proxy_type"] )
        
        try:
            res = self.opener(req)
        except (urllib2.URLError, httplib.BadStatusLine) as e:
            log.error("Endpoint wasn't found on hudson: %s" % req.get_full_url() )
            log.error("Exception: %s" % e.__dict__)
            log.error("Request: %s" % req)
            log.error("Request: %s" % req.__dict__)
            raise e
        except Exception as e:
            contents = e.read()
            log.error(contents) # http errors have content bodies... like servlet
                                # container stacktraces. I'm looking at you, 
                                # Jenkins... -grue
            raise e

        if json_decode:
            res = json.loads(res.read())
        log.info("hudson.req(): '%s' > %s" % ( req.get_full_url(), res ))
        return res


job.Job.register('hudson', Job)
job.Job.register('jenkins', Job)


