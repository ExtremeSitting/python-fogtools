#!/usr/bin/env python

import utils
import json

endpoint = 'https://ord.autoscale.api.rackspacecloud.com/v1.0/%s/%s'
auth_data = utils.auth('samsonite', '07f2ad0df034b776570fe77853159920',
            servicename='cloudServersOpenStack', region='ord')

def findservers(serv):
    '''Returns a server name when given a server uuid.'''
    resp = utils.get('%s/servers/%s' % (auth_data['uri'], serv),
                     auth_data['token'])
    if resp.status_code != 404:
        return resp.json['server']['name']
    else:
        return None

def get_groups():
    '''List out current scaling groups.'''
    resp = utils.get(endpoint % (auth_data['id'], 'groups'),
            auth_data['token']).json
    groups = resp['groups']
    for group in groups:
        utils.printvtable([('Group ID', group['id']),
            ('Desired Capacity', group['desiredCapacity']),
            ('Pending Capacity', group['pendingCapacity']),
            ('Active Capacity', group['activeCapacity']),
            ('Active Nodes',
            utils.string_a_list(
                                [findservers(i) for i in
                                 [i['id'] for i in group['active']]]))])

def make_group(**kwargs):
    '''Needs the name of the group, cooldown, min and max entities, servName
        and lbid'''
    data = {
    "groupConfiguration": {},
    "launchConfiguration": {
        "type": "launch_server",
        "args": {
            "server": {
                "flavorRef": 3,
                "imageRef": "c11fdbb2-808a-4aec-bf12-d531ae053139"
            },
            "loadBalancers": [
                {
                    "loadBalancerId": 141023,
                    "port": 80
                }
            ]
        }
    },
    "scalingPolicies": []
}
    data['groupConfiguration'] = kwargs
#    print json.dumps(data, indent=4)
    resp = utils.post(endpoint % (auth_data['id'], 'groups'),
            data=data, token=auth_data['token'])
    print resp.status_code, resp.json

def delete_group(groupid):
    '''Delete a scaling group.'''
    data = {
    "name": "workers",
    "cooldown": 60,
    "minEntities": 0,
    "maxEntities": 0,
    "metadata": {
                "firstkey": "this is a string",
                "secondkey": "1"
    }
}
    print 'Updating config for group %s...' % groupid
    put = utils.put(endpoint % (auth_data['id'], 'groups/%s/config' % groupid),
                    data=data, token=auth_data['token'])
    print put.status_code, json.dumps(put.json, indent=4)
    delete = utils.delete(endpoint % (auth_data['id'],
            'groups/%s' % groupid), token=auth_data['token'])
    print delete.status_code, json.dumps(delete.json, indent=4)

def make_policy(groupid, **kwargs):
    '''Make a scaling policy.'''
    data = []
    data.append(kwargs)
    resp = utils.post(endpoint % (auth_data['id'], 'groups/%s/policies' % groupid),
                      data=json.dumps(data), token=auth_data['token'])
    print resp.status_code, resp.json

def list_policies(groupid):
    '''List out current scaling policies.'''
    resp = utils.get(endpoint % (auth_data['id'], 'groups/%s/policies' % groupid), token=auth_data['token'])
    data = []
    for i in resp.json['policies']:
        if 'changePercent' in i:
            chng = '%s%%' % i['changePercent']
        else:
            chng = '%s server(s)' % i['change']
        utils.printvtable([('ID', i['id']), ('Name', i['name']),
                ('Change', chng), ('Cooldown', i['cooldown']),
                ('Type', i['type']),
                ('Link', utils.string_a_list([l['href'] for l in i['links']]))])

def delete_policy(polid, groupid):
    '''Deletes a scaling policy'''
    resp = utils.delete(endpoint % (auth_data['id'], 'groups/%s/policies/%s' % (groupid, polid)), token=auth_data['token'])
    print resp.status_code, json.dumps(resp.json, indent=4)

def main():
    '''Parse args and main functions'''
#    make_group('new group test')
    get_groups()
#    findservers('7f037d0c-52be-407d-b900-0e9563ec8227')
#    make_policy('c2964772-d567-4bf7-b522-dc841419b6c7', name='test policy',
#            change=1, cooldown=10, type='webhook')
#    list_policies('c2964772-d567-4bf7-b522-dc841419b6c7')
#    delete_policy('fb6afd6d-74c2-49d6-b1bd-f322d32c56fe',
#            'c2964772-d567-4bf7-b522-dc841419b6c7')
#     delete_group('c2964772-d567-4bf7-b522-dc841419b6c7')
#    delete_group('2b55d518-d66a-402a-8b39-b46393bfd994')
#    delete_group('e159d98b-6e1b-4486-876c-3295cef79811')
#    print auth_data
#    parser = argparse.ArgumentParser()

#    subparsers = parser.add_subparsers(dest='subparsers')
#    list_parser = subparsers.add_parser('list')
#    subsubparsers = subparsers.add_subparsers(dest='subsubparsers')
#    user_subparser = list_parser.add_subparsers()
#    list_parser.add_argument('users')

#    args = parser.parse_args()

if __name__ == '__main__':
    main()
