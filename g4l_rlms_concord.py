# -*-*- encoding: utf-8 -*-*-

import sys
import time
import re
import sys
import urlparse
import json
import datetime
import uuid
import hashlib
import threading
import Queue

from bs4 import BeautifulSoup

from flask.ext.wtf import TextField, PasswordField, Required, URL, ValidationError

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
        response = {
            'reservation_id' : '',
            'load_url' : ''
        }
        return response

def populate_cache():
    pass

CONCORD = register("Concord", ['1.0'], __name__)
CONCORD.add_global_periodic_task('Populating cache', populate_cache, hours = 23)

def main():
    pass

if __name__ == '__main__':
    main()
