#!/usr/bin/env python

import datetime
import time
import sys
import re
import json

from prettytable import PrettyTable as pt

try:
    import human_curl as requests
except:
    import requests


def auth(username, apikey, servicename=None, region=None, debug=False):
    """Auth!
    This may be changed over to httplib in the near future."""
    account_data = {}
    payload = {
        'auth': {'RAX-KSKEY:apiKeyCredentials': {'username': username,
        'apiKey': apikey}}
                }
    headers = {'content-type': 'application/json'}
    response = requests.post('https://identity.api.rackspacecloud.com/v2.0/tokens',
            data=json.dumps(payload), headers=headers)
    auth_data = response.json['access']
    if not servicename:
        raise Exception('servicename must be defined')
    if debug:
        for i in auth_data['serviceCatalog']:
            print i
    else:
        for i in auth_data['serviceCatalog']:
            if i['name'] == servicename:
                if region:
                    for serv in i['endpoints']:
                        if region.upper() == serv['region']:
                            account_data['uri'] = serv['publicURL']
                else:
                    account_data['uri'] = i['endpoints'][0]['publicURL']
        account_data['token'] = auth_data['token']['id']
        account_data['id'] = auth_data['token']['tenant']['id']
        return account_data

def put(uri, data, token=None):
    headers = {
                'X-Auth-Token': token,
                'content-type': 'application/json'
                }
    return requests.put(uri, data=json.dumps(data), headers=headers)

def post(uri, data, token=None):
    headers = {
                'X-Auth-Token': token,
                'content-type': 'application/json'
                }
    return requests.post(uri, data=json.dumps(data), headers=headers)

def get(uri, token=None, headers=None):
    if not headers:
        headers = {
                    'X-Auth-Token': token,
                    'content-type': 'application/json'
                    }
    return requests.get(uri, headers=headers)

def delete(uri, token=None):
    headers = {
                'X-Auth-Token': token,
                'content-type': 'application/json'
                }
    return requests.delete(uri, headers=headers)

def head(uri, token=None):
    headers = {
                'X-Auth-Token': token,
                'content-type': 'application/json'
                }
    return requests.head(uri, headers=headers)

def printhtable(fields, data, sort=None):
    '''Generate a prettytable for output data. Table is generated
    horizontally, much like mysql tables. Fields must be a list and
    data must be a list with the rows as tuples.'''
    table = pt()
    table.field_names = fields
    if sort != None:
        table.sortby = fields[int(sort)]
    else:
        table.sortby = fields[0]
    table.align = 'c'
    table.padding_width = 1
    for row in data:
        table.add_row(row)
    print table

def printvtable(data):
    '''Generate a prettytable for output data. Table is generated
    vertically. Each row only consists of 2 columns and there is no
    "field data". Data should be passed as a list of tuples. The tuples
    represent each row.'''
    fields = ['0', '1']
    table = pt()
    table.field_names = fields
    table.align = 'l'
    table.padding_width = 1
    table.header = False
    for row in data:
        table.add_row(row)
    print table

def converttime(badtime):
    '''This converts time in "2013-04-11T11:12:28" format to standard ctime
    (Thu Apr 11 11:12:28 2013). Because C time is pretty.'''
    zcheck = re.compile(r'Z$',)
    t = re.sub(zcheck, '', badtime)
    YYYY, MM, DD = map(int, t.split('T')[0].split('-'))
    HH, mm, SS = map(int, t.split('T')[1].split(':'))
    isowkdy = int(datetime.date(YYYY, MM, DD).isoweekday())
    isoyr = int(datetime.date(YYYY, MM, DD).strftime('%j'))
    return time.ctime(time.mktime((YYYY, MM, DD, HH, mm, SS, isowkdy, isoyr, -1)))

def string_a_list(lst):
    if not isinstance(lst, list):
        raise TypeError
    else:
        string = None
        for i in lst:
            if not string:
                try:
                    string = i.name
                except AttributeError:
                    string = i
            else:
                try:
                    string = '%s\n%s' % (string ,i.name)
                except AttributeError:
                    string = '%s\n%s' % (string, i)
        return string

def exit(stat):
    '''Exit with status'''
    sys.exit(stat)
