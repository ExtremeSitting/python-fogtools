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

import pyrax.exceptions as exc
import novaclient.exceptions as ncexc


adminpasses = {}

def printhortable(*args):
    '''Generate a prettytable for output data. Table is generated horizontally, 
    much like mysql tables. Fields must be a list and data must be a list with 
    the rows as tuples.'''
    fields, data = args
    table = pyrax.utils.prettytable.PrettyTable()
    table.field_names = fields
    table.sortby = fields[0]
    table.align = 'c'
    table.padding_width = 1
    for row in data:
        table.add_row(row)
    print table

def printvertable(*args):
    '''Generate a prettytable for output data. Table is generated vertically.
    Each row only consists of 2 columns and there is no "field data". Data 
    should be passed as a list of tuples. The tuples represent each row.'''
    fields = ['0', '1']
    data = args[0]
    table = pyrax.utils.prettytable.PrettyTable()
    table.field_names = fields
    table.align = 'l'
    table.padding_width = 1
    table.header = False
    for row in data:
        table.add_row(row)
    print table

def converttime(time):
    '''This converts time in "2013-04-11T11:12:28" format to standard ctime
    (Thu Apr 11 11:12:28 2013). Because C time is pretty.'''
    zcheck = pyrax.utils.re.compile(r'Z$',)
    t = pyrax.utils.re.sub(zcheck, '', time)
    YYYY, MM, DD = t.split('T')[0].split('-')
    HH, mm, SS = t.split('T')[1].split(':')
    isowkdy = pyrax.utils.datetime.date(int(YYYY), int(MM), int(DD)).isoweekday()
    isoyr = pyrax.utils.datetime.date(int(YYYY), int(MM), int(DD)).strftime('%j')
    return pyrax.utils.time.ctime(pyrax.utils.time.mktime((int(YYYY), int(MM),
            int(DD), int(HH), int(mm), int(SS), int(isowkdy), int(isoyr), -1)))

def auth(*args):
    '''Auths the user with API creds. Only supported arg is region (ORD, DFW)'''
    credentials = pyrax.os.environ['HOME'] + '/.rackspace_cloud_credentials'
    if not args:
        pyrax.set_credential_file(credentials)
    else:
        pyrax.set_credential_file(credentials, region=args[0])
    return pyrax.cloudservers

def servercallback(srv):
    '''This function is only used for the wait_until method for threading
    builds. It depends on obj being a server object.'''
    fields = ['Name', 'Password', 'Status', 'IP']
    data = []
    srv.get()
    while 'public' not in srv.networks:
        pyrax.utils.time.sleep(10)
        srv.get()
    ip = [ip for ip in srv.networks['public'] if len(ip) <= 15][0]
    printvertable([('Name', srv.name), ('Pass', adminpasses[srv.id]),
            ('Status', srv.status), ('IP', ip)])

def listservers(*args):
    '''Print out servers in account'''
    auth()
    fields = ['Name', 'DC', 'Status', 'Public IPv4', 'Public IPv6',
            'Private IPv4', 'Date Created', 'Server ID']
    servdata = []
    dfwservers = pyrax.connect_to_cloudservers(region='DFW')
    ordservers = pyrax.connect_to_cloudservers(region='ORD')
    for server in dfwservers.servers.list():
        servdata.append((server.name, 'DFW', server.status,
                [v4 for v4 in server.networks['public'] if len(v4) <= 15][0],
                [v6 for v6 in server.networks['public'] if len(v6) >= 16][0],
                [pri for pri in server.networks['private'] if len(pri) <= 15][0],
                converttime(server.created), server.id))
    for server in ordservers.servers.list():
        servdata.append((server.name, 'ORD', server.status,
                [v4 for v4 in server.networks['public'] if len(v4) <= 15][0],
                [v6 for v6 in server.networks['public'] if len(v6) >= 16][0],
                [pri for pri in server.networks['private'] if len(pri) <= 15][0],
                converttime(server.created), server.id))
    printhortable(fields, servdata)

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
                    converttime(image.created), image.id))
    for image in dfwservers.images.list():
        if image.metadata['image_type'] == 'snapshot':
            try:
                snaps.append((image.name, image.status, 'DFW',
                        image.server['id'], converttime(image.created),
                        image.id))
            except AttributeError:
                snaps.append((image.name, image.status, 'DFW',
                        'Server Deleted', converttime(image.created),
                        image.id))
    for image in ordservers.images.list():
        if image.metadata['image_type'] == 'snapshot':
            try:
                snaps.append((image.name, image.status, 'ORD',
                        image.server['id'], converttime(image.created),
                        image.id))
            except AttributeError:
                snaps.append((image.name, image.status, 'ORD',
                        'Server Deleted', converttime(image.created),
                        image.id))
    printhortable(basefields, baseimages)
    printhortable(snapfields, snaps)

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
                'DFW', converttime(lb.created['time']), lb.id))
    for lb in ordlbs.list():
        lbdata.append((lb.name, lb.status, str(lb.nodeCount), lb.protocol,
                'ORD', converttime(lb.created['time']), lb.id))
    printhortable(fields, lbdata)

def listlbproto():
    auth()
    lb = pyrax.cloud_loadbalancers
    protodata = []
    for p in lb.protocols:
        protodata.append((p,))
    printhortable(['Name'], protodata)

def addtolb():
    auth()

def massbuild(*args, **kwargs):
    '''Provide a basename and an amount. This function will build the amount
    specified starting at 1. Default naming convention is "web1, web2, web3".
    If wait is False, returned build data is provided immediatly. It is likely
    that the network info will be unavailable until the build completes.'''
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
    printvertable([('Name: ', basename), ('Size: ', size), ('Amount: ', amount),
            ('Start at: ', start)])
    build = raw_input('Is this information correct? (y|n) ')
    if build.lower() == 'y':
        for count in range(start, start + amount):
            server = cs.servers.create(basename + str(count), imageid,
            flavor)
            if not kwargs['nowait']:
                print 'Building %s...' % server.name
                pyrax.utils.wait_until(server, 'status', ['ACTIVE', 'ERROR'],
                        callback=servercallback, attempts=0)
                adminpasses[server.id] = server.adminPass
            else:
                printvertable([('Name', server.name), ('Pass', server.adminPass),
                        ('Status', server.status), ('IP', server.networks)])
    else:
        exit(0)

def exit(stat):
    print 'Exiting...'
    pyrax.utils.sys.exit(stat)

def buildlb(name, size, *args, **kwargs):
    '''Build Loadbalancer.'''
    cs = auth()
    lb = pyrax.cloud_loadbalancers()
    name = kwargs['name']
    port = kwargs['port']
    protocol = kwargs['protocol'].upper()
    algorithm = kwargs['algorithm'].upper()
    vip = kwargs['vip'].upper()
    nodes = kwargs['nodes']
    nodeips = []
    if len(nodes) > 25:
        print 'Only 25 nodes can be added to one loadbalancer.'
    else:
        for uuid in nodes:
            nodeips.append(cs.servers.get(uuid).networks['private'])
        newlb = lb.create(name, port=port, protocol=protocol,
                algorithm=algorithm, vip=vip, nodes=nodeips)
    

def main():
    '''Parse all CLI arguments.'''
    parser = argparse.ArgumentParser()

    subparsers = parser.add_subparsers(dest='subparsers')
## List arguments
    parser_list = subparsers.add_parser('list')
    parser_list.add_argument('--servers', action='store_true',
            help='List servers on account.')
    parser_list.add_argument('--images', action='store_true',
            help='List images on account.')
    parser_list.add_argument('--lbs', action='store_true',
            help='List loadbalancers on account.')
    parser_list.add_argument('--lb-protocols', action='store_true')
#    parser_list.add_argument('--')
## Build arguments
    parser_build = subparsers.add_parser('build')



#    subsubparsers = subparser.add_subparsers(dest='subsubparsers')
## Servers
    parser_build.add_argument('--servers', action='store_true',
            dest='build_server')
    parser_build.add_argument('-n', '--name', action='store', type=str,
            default='web')
    parser_build.add_argument('-s', '--size', action='store', type=int,
            default=512)
    parser_build.add_argument('-a', '--amount', action='store', type=int,
            default=3)
    parser_build.add_argument('-S', '--start-at', action='store', type=int,
            default=1)
    parser_build.add_argument('-i', '--image', action='store', type=str)
    parser_build.add_argument('-r', '--region', action='store', type=str)
    parser_build.add_argument('--lb-name', action='store', type=str)
    parser_build.add_argument('--no-wait', action='store_true')
### Loadbalancers
#    parser_build.add_argument('--lbs', action='store_true', dest='build_lb')
##    parser_build.add_argument('-n', '--name', action='store', type=str,
##            required=True)
#    parser_build.add_argument('-p', '--port', action='store', type=str,
#            default=80, metavar='#')
#    parser_build.add_argument('-P', '--protocol', action='store', type=str,
#            default='http')
#    parser_build.add_argument('--algorithm', action='store',
#            choices=['least_connections', ' random', ' round_robin',
#                    ' weighted_least_connections', ' weighted_round_robin'],
#                    default='round_robin')
#    parser_build.add_argument('--ip', action='store',
#            choices=['public', 'private'], default='public')
#    parser_build.add_argument('-N', '--nodes', action='store', type=str,
#            nargs='*', required=True, metavar='ID')
    args = parser.parse_args()

#    print parser.parse_args(['-n', 'sam'])

    if args.subparsers == 'list':
        if args.servers:
            listservers()
        elif args.images:
            listimages()
        elif args.lbs:
            listlbs()
        elif args.lb_protocols:
            listlbproto()
    elif args.subparsers == 'build':
        if args.build_server:
            massbuild(basename=args.name, size=args.size, imageid=args.image,
            amount=args.amount, start=args.start_at, region=args.region,
            nowait=args.no_wait)
#        elif args.build_lb:
#            build_lb(name=args.name, port=args.port, protocol=args.protocol,
#                    algorithm=args.algorithm, vip=args.ip, nodes=args.nodes)
if __name__ == '__main__':
    main()
