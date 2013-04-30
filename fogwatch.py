#!/usr/bin/env python

import argparse
import json
import uuid
import sys

import human_curl as requests

account_data = {}
targets = {}
checkdata = { 
                "details" : {},
                "label" : "Ping Check %s",
                "monitoring_zones_poll" : [ "mzdfw" ],
                "period" : "30",
                "target_alias" : "%s",
                "timeout" : 5,
                "type" : "remote.ping"
            }

def auth(username, apikey):
    """Auth!
    This may be changed over to httplib in the near future."""
    payload = {
        'auth': {'RAX-KSKEY:apiKeyCredentials': {'username': username,
        'apiKey': apikey}}
                }
    headers = {'content-type': 'application/json'}
    response = requests.post('https://auth.api.rackspacecloud.com/v2.0/tokens',
            data=json.dumps(payload), headers=headers)
    auth_data = response.json['access']
    for i in auth_data['serviceCatalog']:
        if i['name'] == 'cloudMonitoring':
            endpoint = i['endpoints'][0]['publicURL']
    account_data['token'] = auth_data['token']['id']
    account_data['monuri'] = endpoint

def post(uri, data):
    headers = {
                'X-Auth-Token': account_data['token'],
                'content-type': 'application/json'
                }
    return requests.post(uri, data=data, headers=headers)

def get(uri):
    headers = {
                'X-Auth-Token': account_data['token'],
                'content-type': 'application/json'
                }
    return requests.get(uri, headers=headers)

def delete(uri):
    headers = {
                'X-Auth-Token': account_data['token'],
                'content-type': 'application/json'
                }
    return requests.delete(uri, headers=headers)

#def listzones():
#    print type(get('%s/monitoring_zones' % account_data['monuri']).json)

def makeentities(ips, **kwargs):
    postdata = {
                'ip_addresses' : { '%s' : '%s' },
                'label' : '%s',
                'metadata' : {  }
                }
    if isinstance(ips, list):
        if 'debug' in kwargs:
            for n, i in enumerate(ips):
                check_uuid = uuid.uuid1()
                print '%s %s %s %s' % (n, i, '%s/entities/' % account_data['monuri'],
                        json.dumps(json.loads(json.dumps(postdata) % (n, i,
                                check_uuid)), indent=4))
                targets[n] = (i, '%s/entities/%s' % (account_data['monuri'], i),
                        check_uuid)
        else:
            for n, i in enumerate(ips):
                check_uuid = uuid.uuid1()
                resp = post('%s/entities/' % account_data['monuri'],
                        json.dumps(postdata) % (n, i, check_uuid))
                targets[n] = { 
                        'ip' : i,
                        'check_uuid' : check_uuid,
                        'ent' : resp.headers['location'].split('/')[6]
                        }
            makechecks()

def makechecks(**kwargs):
    if 'debug' in kwargs:
        for item in targets.keys():
            print '%s/checks\n%s' % (account_data['monuri'],
                    json.dumps(json.loads(json.dumps(checkdata) % (item,
                            targets[item]['check_uuid'])), indent=4))
    else:
        for item in targets.keys():
            resp = post('%s/entities/%s/checks' % (account_data['monuri'],
                    targets[item]['ent']),
                    json.dumps(checkdata) % (item,
                            targets[item]['check_uuid']))
            if int(resp.status_code) < 299:
                print 'Check for %s made. UUID: %s' % (targets[item]['ip'],
                        targets[item]['check_uuid'])
                targets[item]['check'] = resp.headers['location'].split('/')[8]
            else:
                print 'Check for %s FAILED. UUID: %s \n%s\n%s' % (targets[item]['ip'],
                        targets[item]['check_uuid'], resp.reason, resp.text)
                exit(1)

def makenotify():
    notedata = {
                "details" : { "address" : "sam.chapler@rackspace.com" },
                "label" : "Highlights Alert",
                "type" : "email"
                }
    noteplan = {
            "label": "Highlights Plan",
            "warning_state": [ "%s" ],
            "critical_state": [ "%s" ],
            "ok_state": [ "%s" ]
            }
    noteresp = post('%s/notifications' % account_data['monuri'],
            json.dumps(notedata))
    if int(noteresp.status_code) > 299:
        print 'Unable to setup notification. Reason: %s' % noteresp.reason
        exit(1)
    else:
        account_data['note'] = noteresp.headers['location'].split('/')[6]
        planresp = post('%s/notification_plans' % account_data['monuri'],
                json.dumps(noteplan) % (account_data['note'], account_data['note'],
                        account_data['note']))
    if int(planresp.status_code) > 299:
        print 'Unable to setup notification plan. Reason: %s' % planresp.reason
        exit(1)
    else:
        account_data['plan'] = planresp.headers['location'].split('/')[6]

def makealarm():
    alarmdata = {
            "check_id": "%s",
            "notification_plan_id": "%s",
            "criteria": "if (metric[\"duration\"] < 100) { return OK } return WARNING"
                }
    for item in targets.keys():
        alarmresp = post('%s/entities/%s/alarms' % (account_data['monuri'],
                targets[item]['ent']),
                json.dumps(alarmdata) % (targets[item]['check'],
                        account_data['plan']))

def listplans():
    for r1 in get('%s/notifications' % account_data['monuri']).json:
        print
    resp2 = get('%s/notification_plans' % account_data['monuri'])
#    return resp1.json, resp2.json

def cleanup():
    notes, plans = listplans()
    for item in notes['values']:
        resp = delete('%s/notifications/%s' % (account_data['monuri'], item['id']))
        if int(resp.status_code) < 299:
            print 'Notification %s deleted' % item['id']
    for item in plans['values']:
        resp = delete('%s/notification_plans/%s' % (account_data['monuri'], item['id']))
        if int(resp.status_code) < 299:
            print 'Plan %s deleted' % item['id']

def exit(stat):
    sys.exit(stat)

def main():
    parser = argparse.ArgumentParser(description='Usage: %prog [username] \
        [apikey] options')
    parser.add_argument(
        'username', metavar='[USERNAME]', help='API Username', type=str,
        action='store')
    parser.add_argument(
        'apikey', metavar='[APIKEY]', help='API Username', type=str,
        action='store')
    parser.add_argument('ips', type=str, nargs='*')
    parser.add_argument('--plan', action='store_true')
    parser.add_argument('--list-plans', action='store_true')
    parser.add_argument('--debug', action='store_true')
    parser.add_argument('--clean', action='store_true')

    args = parser.parse_args()

    auth(args.username, args.apikey)
    if args.debug:
        makeentities(args.ips, debug=True)
        makechecks(debug=True)
    elif args.clean:
        cleanup()
    elif args.plan:
        makenotify()
    elif args.list_plans:
        print listplans()
    else:
        makenotify()
        makeentities(args.ips)
        makealarm()
if __name__ == '__main__':
    main()
