#!/usr/bin/env python
         #   Copyright 2013 Sam Chapler
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
import pyrax
import argparse
import utils

import pyrax.exceptions as exc
import novaclient.exceptions as ncexc

from sys import exit
from os import environ
from time import sleep

adminpasses = {}
server_return = []

def auth(*args):
    '''Auths the user with API creds. Only supported arg is region (ORD, DFW)'''
    credentials = environ['HOME'] + '/.rackspace_cloud_credentials'
    if not args:
        pyrax.set_credential_file(credentials)
    else:
        pyrax.set_credential_file(credentials, region=args[0])
    return pyrax.cloudservers

def servercallback(srv):
    '''This function is only used for the wait_until method for threading
    builds. It depends on obj being a server object.'''
    srv.get()
    while 'public' not in srv.networks:
        sleep(3)
        srv.get()
    ip = [ip for ip in srv.networks['public'] if len(ip) <= 15][0]
#    utils.printvtable([('Name', srv.name), ('Pass', adminpasses[srv.id]),
#            ('Status', srv.status), ('IP', ip)])
    server_return.append((srv.id, srv.name, adminpasses[srv.id], srv.status, ip))

def listservers(*args):
    '''Print out servers in account'''
    auth()
    fields = ['Name', 'DC', 'Status', 'Public IPv4',
            'Private IPv4', 'Date Created', 'Server ID', 'Image']
    servdata = []
    dfwservers = pyrax.connect_to_cloudservers(region='DFW')
    ordservers = pyrax.connect_to_cloudservers(region='ORD')
    for server in dfwservers.servers.list():
        servdata.append((server.name, 'DFW', server.status,
                [pub for pub in server.networks['public'] if len(pub) <= 15][0],
                [pri for pri in server.networks['private'] if len(pri) <= 15][0],
                utils.converttime(server.created), server.id, findimage(server.image['id'])))
    for server in ordservers.servers.list():
        servdata.append((server.name, 'ORD', server.status,
                [pub for pub in server.networks['public'] if len(pub) <= 15][0],
                [pri for pri in server.networks['private'] if len(pri) <= 15][0],
                utils.converttime(server.created), server.id, findimage(server.image['id'])))
    utils.printhtable(fields, servdata)

def listimages(*args):
    '''Print out all images including base images in account'''
    cs = auth()
    basefields = ['Name', 'Status', 'Created at', 'ID']
    snapfields = ['Name', 'Status', 'DC', 'Parent', 'Created at', 'ID']
    baseimages = []
    snaps = []
    dfwservers = pyrax.connect_to_cloudservers(region='DFW')
    ordservers = pyrax.connect_to_cloudservers(region='ORD')
    for image in cs.images.list():
        if image.metadata['image_type'] == 'base':
            baseimages.append((image.name, image.status,
                    utils.converttime(image.created), image.id))
    for image in dfwservers.images.list():
        if image.metadata['image_type'] == 'snapshot':
            try:
                snaps.append((image.name, image.status, 'DFW',
                        image.server['id'], utils.converttime(image.created),
                        image.id))
            except AttributeError:
                snaps.append((image.name, image.status, 'DFW',
                        'Server Deleted', utils.converttime(image.created),
                        image.id))
    for image in ordservers.images.list():
        if image.metadata['image_type'] == 'snapshot':
            try:
                snaps.append((image.name, image.status, 'ORD',
                        image.server['id'], utils.converttime(image.created),
                        image.id))
            except AttributeError:
                snaps.append((image.name, image.status, 'ORD',
                        'Server Deleted', utils.converttime(image.created),
                        image.id))
    utils.printhtable(basefields, baseimages)
    utils.printhtable(snapfields, snaps)

def findimage(imageid):
    dfwservers = pyrax.connect_to_cloudservers(region='DFW')
    ordservers = pyrax.connect_to_cloudservers(region='ORD')
    try:
        return dfwservers.images.get(imageid).name
    except ncexc.NotFound:
        return ordservers.images.get(imageid).name
    except ncexc.NotFound:
        return 'Image Deleted'

def listlbs(*args):
    '''Print out all loadbalancers'''
    auth()
    fields = ['Name', 'Status', 'Node Count', 'Protocol', 'Region',
            'Created at', 'ID']
    lbdata = []
    dfwlbs = pyrax.connect_to_cloud_loadbalancers(region='DFW')
    ordlbs = pyrax.connect_to_cloud_loadbalancers(region='ORD')
    for lb in dfwlbs.list():
        lbdata.append((lb.name, lb.status, str(lb.nodeCount), lb.protocol,
                'DFW', utils.converttime(lb.created['time']), lb.id))
    for lb in ordlbs.list():
        lbdata.append((lb.name, lb.status, str(lb.nodeCount), lb.protocol,
                'ORD', utils.converttime(lb.created['time']), lb.id))
    utils.printhtable(fields, lbdata)

def massbuild(*args, **kwargs):
    '''Provide a basename and an amount. This function will build the amount
    specified starting at 1. Default naming convention is "web1, web2, web3".
    If wait is False, returned build data is provided immediatly. It is likely
    that the network info will be unavailable until the build completes.'''
    if kwargs['disk'] is False:
        disk = 'AUTO'
    else:
        disk = 'MANUAL'
    if kwargs['password']:
        password = kwargs['password']
    if kwargs['region'] is None:
        region = kwargs['region']
    else:
        region = kwargs['region'].upper()
    cs = auth(region)
    basename = kwargs['basename']
    size = kwargs['size']
    for flvr in cs.flavors.list():
        if size == int(flvr.ram):
            flavor = flvr.id
    if kwargs['imageid'] is None:
        for image in cs.images.list():
            if 'Squeeze' in image.name:
                imageid = image.id
    else:
        imageid = kwargs['imageid']
        try:
            cs.images.get(imageid)
        except ncexc.NotFound:
            print 'Image not found. It may not be local to %s.' % cs.client.region_name
            exit(1)
    start = kwargs['start']
    amount = kwargs['amount']
    utils.printvtable([('Name: ', basename), ('Size: ', size),
            ('Amount: ', amount), ('Start at: ', start)])
    build = raw_input('Is this information correct? (y|n) ')
    if build.lower() == 'y':
        for count in range(start, start + amount):
            server = cs.servers.create(basename + str(count), imageid,
            flavor, disk_config=disk)
            if not kwargs['nowait']:
                print 'Building %s...' % server.name
                pyrax.utils.wait_until(server, 'status', ['ACTIVE', 'ERROR'],
                        callback=servercallback, attempts=0)
                if not password:
                    adminpasses[server.id] = server.adminPass
                else:
                    adminpasses[server.id] = password
            else:
                utils.printvtable([('Name', server.name),
                        ('Pass', server.adminPass), ('Status', server.status),
                        ('IP', server.networks)])
        while len(server_return) != amount:
            pyrax.utils.time.sleep(5)
        if password:
            print 'Changing passwords to %s...' % password
            for s in server_return:
                cs.servers.change_password(s[0], password)
                print 'Password changed for %s' % s[1]
        fields = ['ID', 'Name', 'Password', 'Status', 'IP']
        utils.printhtable(fields, server_return, sort=1)
    else:
        exit(0)

def main():
    '''Parse all CLI arguments.'''
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest='subparsers')
## List arguments
    list_subparser = subparsers.add_parser('list')
    list_subparser.add_argument('--servers', action='store_true',
            help='List servers on account.')
    list_subparser.add_argument('--images', action='store_true',
            help='List images on account.')
    list_subparser.add_argument('--lbs', action='store_true',
            help='List loadbalancers on account.')
    list_subparser.add_argument('--lb-protocols', action='store_true')
## Build arguments
    build_subparser = subparsers.add_parser('build')
## Servers
    build_subparser.add_argument('--servers', action='store_true',
            dest='build_server')
    build_subparser.add_argument('-n', '--name', action='store', type=str,
            default='web')
    build_subparser.add_argument('-s', '--size', action='store', type=int,
            default=512)
    build_subparser.add_argument('-a', '--amount', action='store', type=int,
            default=3)
    build_subparser.add_argument('-S', '--start-at', action='store', type=int,
            default=1)
    build_subparser.add_argument('-i', '--image', action='store', type=str)
    build_subparser.add_argument('-r', '--region', action='store', type=str)
    build_subparser.add_argument('-P', '--password', action='store', type=str)
    build_subparser.add_argument('-f', '--files', nargs='*', action='store',
            type=str)
    build_subparser.add_argument('--no-wait', action='store_true')
    build_subparser.add_argument('--no-disk-config', action='store_true',
            default=False)

    args = parser.parse_args()

    if args.subparsers == 'list':
        if args.servers:
            listservers()
        elif args.images:
            listimages()
        elif args.lbs:
            listlbs()
    elif args.subparsers == 'build':
        if args.build_server:
#            if len(args.files) > 5:
#                print 'Too many files. 5 files max.'
#                exit(1)
#            else:
#                dfiles = {}
#                for filename in args.files:
#                    with open(filename) as f:
#                        data = f.read()
#                        dfiles[filename] = data
#            print files.items()
            massbuild(basename=args.name, size=args.size, imageid=args.image,
            amount=args.amount, start=args.start_at, region=args.region,
            password=args.password, nowait=args.no_wait, files=None,
            disk=args.no-disk-config)
if __name__ == '__main__':
    main()
