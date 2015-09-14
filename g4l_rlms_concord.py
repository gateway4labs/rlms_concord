# -*-*- encoding: utf-8 -*-*-

import sys
import json
import urllib2
import datetime

from labmanager.forms import AddForm
from labmanager.rlms import register, Laboratory, CacheDisabler
from labmanager.rlms.base import BaseRLMS, BaseFormCreator, Capabilities, Versions

DEBUG = False
    
def dbg(msg):
    if DEBUG:
        print msg
        sys.stdout.flush()

class ConcordAddForm(AddForm):

    DEFAULT_URL = 'http://lab.concord.org/'
    DEFAULT_LOCATION = 'Concord, MA, USA'
    DEFAULT_PUBLICLY_AVAILABLE = True
    DEFAULT_PUBLIC_IDENTIFIER = 'concord'
    DEFAULT_AUTOLOAD = True

    def __init__(self, add_or_edit, *args, **kwargs):
        super(ConcordAddForm, self).__init__(*args, **kwargs)
        self.add_or_edit = add_or_edit

    @staticmethod
    def process_configuration(old_configuration, new_configuration):
        return new_configuration

class ConcordFormCreator(BaseFormCreator):

    def get_add_form(self):
        return ConcordAddForm

FORM_CREATOR = ConcordFormCreator()

MIN_TIME = datetime.timedelta(hours=24)

def retrieve_labs():
    KEY = 'get_laboratories'
    labs = CONCORD.cache.get(KEY, min_time = MIN_TIME)
    if labs:
        return labs

    dbg("get_laboratories not in cache")
    laboratories = []
    interactive_list = CONCORD.cached_session.timeout_get("http://lab.concord.org/interactives.json").json()
    for interactive in interactive_list.get('interactives', []):
        if 'path' not in interactive:
            continue

        name = interactive.get('title', 'no title')
        link = urllib2.quote(interactive['path'], '')
        description = interactive.get('subtitle', '')
        lab = Laboratory(name = name, laboratory_id = link, autoload = True, description = description)
        laboratories.append(lab)

    CONCORD.cache[KEY] = laboratories
    return laboratories    

class RLMS(BaseRLMS):

    def __init__(self, configuration, *args, **kwargs):
        self.configuration = json.loads(configuration or '{}')

    def get_version(self):
        return Versions.VERSION_1

    def get_capabilities(self):
        return []

    def get_laboratories(self, **kwargs):
        return retrieve_labs()

    def reserve(self, laboratory_id, username, institution, general_configuration_str, particular_configurations, request_payload, user_properties, *args, **kwargs):
        url = 'http://lab.concord.org/embeddable.html#{0}'.format(urllib2.unquote(laboratory_id))
        response = {
            'reservation_id' : url,
            'load_url' : url
        }
        return response

def populate_cache():
    rlms = RLMS("{}")
    rlms.get_laboratories()

CONCORD = register("Concord", ['1.0'], __name__)
CONCORD.add_global_periodic_task('Populating cache', populate_cache, hours = 23)

def main():
    rlms = RLMS("{}")
    t0 = time.time()
    laboratories = rlms.get_laboratories()
    tf = time.time()
    print len(laboratories), (tf - t0), "seconds"
    for lab in laboratories[:5]:
        t0 = time.time()
        print rlms.reserve(lab.laboratory_id, 'tester', 'foo', '', '', '', '', locale = lang)
        tf = time.time()
        print tf - t0, "seconds"

if __name__ == '__main__':
    main()
