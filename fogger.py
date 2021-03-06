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
    server_return.append((srv.id, srv.name, adminpasses[srv.id], srv.status, ip))

def listservers(*args):
    '''Print out servers in account'''
    auth()
    fields = ['Name', 'DC', 'Status', 'Public IPv4',
            'Private IPv4', 'Date Created', 'Server ID', 'Image']
    servdata = []
    c2cs = pyrax.connect_to_cloudservers
    for reg in pyrax.regions:
        for server in c2cs(region=reg).list():
            servdata.append((server.name, reg, server.status,
                    [pub for pub in server.networks['public'] if len(pub) <= 15][0],
                    [pri for pri in server.networks['private'] if len(pri) <= 15][0],
                    utils.converttime(server.created), server.id,
                    findimage(server.image['id'])))
    utils.printhtable(fields, servdata)

def listimages():
    cs = auth()
    c2cs = pyrax.connect_to_cloudservers
    basefields = ['Name', 'Status', 'Created at', 'ID']
    snapfields = ['Name', 'Status', 'DC', 'Parent', 'Created at', 'ID']
    baseimages = []
    snaps = []
    for image in cs.list_base_images():
        baseimages.append((image.name, image.status,
                utils.converttime(image.created), image.id))
    for reg in pyrax.regions:
        for image in c2cs(region=reg).list_snapshots():
            try:
                snaps.append((image.name, image.status, reg,
                        image.server['id'],
                        utils.converttime(image.created), image.id))
            except AttributeError:
                snaps.append((image.name, image.status, reg,
                        'Server Deleted', utils.converttime(image.created),
                        image.id))
    utils.printhtable(basefields, baseimages)
    utils.printhtable(snapfields, snaps)

def list_flavors():
    cs = auth()
    c2cs = pyrax.connect_to_cloudservers
    fields = ['ID', 'Region','Name', 'RAM', 'Swap', 'Disk', 'Network', 'vCPUs']

    for reg in pyrax.regions:
        flavors = []
        for flav in c2cs(region=reg).list_flavors():
            flavors.append((flav.id, reg, flav.name, flav.ram, flav.swap,
                    flav.disk, flav.rxtx_factor, flav.vcpus))
        utils.printhtable(fields, flavors, sort=0)
        del flavors

def findimage(imageid):
    c2cs = pyrax.connect_to_cloudservers
    for reg in pyrax.regionsr:
        try:
            return c2cs(region=reg).images.get(imageid).name
        except ncexc.NotFound:
            continue

def listlbs(*args):
    '''Print out all loadbalancers'''
    auth()
    fields = ['Name', 'Status', 'Node Count', 'Protocol', 'Region',
            'Created at', 'ID']
    lbdata = []
    c2lb = pyrax.connect_to_cloud_loadbalancers
    for reg in pyrax.region:
        for lb in c2lb(region=reg).list():
            lbdata.append((lb.name, lb.status, str(lb.nodeCount), lb.protocol,
                    reg, utils.converttime(lb.created['time']), lb.id))
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
    auth()
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest='subparsers')
## List arguments
    list_subparser = subparsers.add_parser('list')
    list_subparser.add_argument('--servers', action='store_true',
            help='List servers on account.')
    list_subparser.add_argument('--images', action='store_true',
            help='List images on account.')
    list_subparser.add_argument('--image', action='store', type=str,
            help='List images on account.')
    list_subparser.add_argument('--flavors', action='store_true')
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
    build_subparser.add_argument('-r', '--region', action='store', type=str,
            choices=pyrax.regions)
    build_subparser.add_argument('-P', '--password', action='store', type=str)
    build_subparser.add_argument('--no-wait', action='store_true')
    build_subparser.add_argument('--no-disk-config', action='store_true',
            default=False)

    args = parser.parse_args()

    if args.subparsers == 'list':
        if args.servers:
            listservers()
        elif args.images:
            listimages()
        elif args.image:
            findimage(args.image)
        elif args.flavors:
            list_flavors()
        elif args.lbs:
            listlbs()
    elif args.subparsers == 'build':
        if args.build_server:
            massbuild(basename=args.name, size=args.size, imageid=args.image,
            amount=args.amount, start=args.start_at, region=args.region,
            password=args.password, nowait=args.no_wait, files=None,
            disk=args.no_disk_config)
if __name__ == '__main__':
    main()
