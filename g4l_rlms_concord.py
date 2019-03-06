# -*-*- encoding: utf-8 -*-*-

import sys
import json
import time
import urllib2
import datetime
import threading

from Queue import Queue, Empty

import requests

from labmanager.forms import AddForm
from labmanager.rlms import register, Laboratory, CacheDisabler, LabNotFoundError
from labmanager.rlms.base import BaseRLMS, BaseFormCreator, Capabilities, Versions

DEBUG = False
    
def dbg(msg):
    if DEBUG:
        print msg
        sys.stdout.flush()

class ConcordAddForm(AddForm):

    DEFAULT_URL = 'https://lab.concord.org/'
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

class Runner(threading.Thread):
    def __init__(self, shared_queue, shared_data):
        threading.Thread.__init__(self)
        self.daemon = True
        self.shared_queue = shared_queue
        self.shared_data = shared_data

    def run(self):
        s = requests.Session()
        
        while True:
            try:
                lab = self.shared_queue.get_nowait()
            except Empty:
                break

            identifier = lab['path']
            self.shared_data[identifier] = {
                'title': lab.get('title', 'no title'),
                'description': lab.get('subtitle', ''),
                'id': urllib2.quote(lab['path'], ''),
                'locales': {}
            }

            r = s.get("https://lab.concord.org/locales/metadata/" + lab['path'])
            try:
                r.raise_for_status()
                json_contents = r.json()
            except Exception as e:
                self.shared_data[identifier]['locales']['en'] = lab['path']
            else:
                for lang, lang_url in json_contents.items():
                    lang_name = lang.split('-')[0]
                    lang_url = 'https://lab.concord.org/' + lang_url
                    self.shared_data[identifier]['locales'][lang_name] = lang_url

THREADS = 10

def retrieve_all_links():
    KEY = 'get_all_links'
    links = CONCORD.cache.get(KEY, min_time=MIN_TIME)
    if links:
        return links

    shared_queue = Queue()
    shared_data = {
    #   quoted_path : {
    #       'title': title,
    #       'description': description,
    #       'locales': {
    #           language: url
    #       }
    #   }
    }

    contents = requests.get("https://lab.concord.org/interactives.json").json()
    for lab in contents['interactives']:
        shared_queue.put(lab)

    _threads = []
    for t in range(THREADS):
        r = Runner(shared_queue, shared_data)
        r.start()
        _threads.append(r)
    
    any_alive = True
    while any_alive:
        any_alive = False
        for t in _threads:
            if t.isAlive():
                any_alive = True
        time.sleep(0.05)
    
    CONCORD.cache[KEY] = shared_data
    return shared_data

def retrieve_labs():
    KEY = 'get_laboratories'
    labs = CONCORD.cache.get(KEY, min_time = MIN_TIME)
    if labs:
        return labs

    dbg("get_laboratories not in cache")
    links = retrieve_all_links()
    laboratories = []
    for link_id, link_data in links.items():
        lab = Laboratory(name = link_data['title'], laboratory_id = link_data['id'], autoload = True, description = link_data['description'])
        laboratories.append(lab)
        
    CONCORD.cache[KEY] = laboratories
    return laboratories    

class RLMS(BaseRLMS):

    def __init__(self, configuration, *args, **kwargs):
        self.configuration = json.loads(configuration or '{}')

    def get_version(self):
        return Versions.VERSION_1

    def get_capabilities(self):
        return [Capabilities.TRANSLATION_LIST, Capabilities.URL_FINDER, Capabilities.CHECK_URLS ]

    def get_base_urls(self):
        return [ 'http://lab.concord.org/', 'https://lab.concord.org/' ]

    def get_lab_by_url(self, url):
        for lab in retrieve_labs():
            if urllib2.unquote(lab.laboratory_id) in url:
                return lab
        return None

    def get_laboratories(self, **kwargs):
        return retrieve_labs()

    def get_translation_list(self, laboratory_id):
        links = retrieve_all_links()
        for link, link_data in links.items():
            if link == laboratory_id or link == requests.utils.unquote(laboratory_id):
                return dict(supported_languages=link_data['locales'].keys())

        return {
            'supported_languages' : ['en']
        }

    def get_check_urls(self, laboratory_id):
        links = retrieve_all_links()
        lab = links.get(laboratory_id)

        check_urls = []
        for locale_url in lab['locales'].values():
            check_urls.append('https://lab.concord.org/embeddable.html#{0}'.format(locale_url))

        return check_urls

    def reserve(self, laboratory_id, username, institution, general_configuration_str, particular_configurations, request_payload, user_properties, *args, **kwargs):
        links = retrieve_all_links()
        lab = links.get(laboratory_id)
        if lab is None:
            raise LabNotFoundError("Lab not found: {!r} in {!r}".format(laboratory_id, links.keys()))

        locale = kwargs.get('locale', 'en')
        if '_' in locale:
            locale = locale.split('_')[0]
        locale_url = lab['locales'].get(locale)
        if locale_url is None:
            locale_url = lab['locales'].get('en')
            if locale_url is None:
                raise LabNotFoundError("Lab not found in English: {}".format(laboratory_id))
        
        url = 'https://lab.concord.org/embeddable.html#{0}'.format(locale_url)
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
        for lang in ('es', 'en'):
            t0 = time.time()
            print rlms.reserve(lab.laboratory_id, 'tester', 'foo', '', '', '', '', locale = lang)
            tf = time.time()
            print tf - t0, "seconds"

    for lab in laboratories:
        if 'pollution' not in lab.laboratory_id:
            continue
        for lang in ('es', 'en'):
            t0 = time.time()
            print rlms.reserve(lab.laboratory_id, 'tester', 'foo', '', '', '', '', locale = lang)
            tf = time.time()
            print tf - t0, "seconds"

    links = retrieve_all_links()
    import json
    open('contents.json', 'w').write(json.dumps(links, indent=4))

if __name__ == '__main__':
    main()
