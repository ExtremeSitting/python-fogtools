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


def printhortable(*args):
    '''Generate a prettytable for output data. Table is generated horizontally, 
    much like mysql tables. Fields must be a list and data must be a list with 
    the rows as tuples.'''
    fields, data = args
    table = pyrax.utils.prettytable.PrettyTable()
    table.field_names = fields
    table.sortby = fields[0]
    table.align = 'l'
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

def auth(*args):
    '''Auths the user with API creds. Only supported arg is region (ORD, DFW)'''
    credentials = pyrax.os.environ['HOME'] + '/.rackspace_cloud_credentials'
    if not args:
        pyrax.set_credential_file(credentials)
    else:
        pyrax.set_credential_file(credentials, args[0])
    return pyrax.cloudservers

def listservers():
    '''Print out servers in account'''
    auth()
    fields = ['Name', 'DC', 'Status', 'Date Created', 'Server ID']
    servdata = []
    dfwservers = pyrax.connect_to_cloudservers(region='DFW')
    ordservers = pyrax.connect_to_cloudservers(region='ORD')
    for server in dfwservers.servers.list():
        servdata.append((server.name, 'DFW', server.status, server.created,
                server.id))
    for server in ordservers.servers.list():
        servdata.append((server.name, 'ORD', server.status, server.created,
                server.id))
    printhortable(fields, servdata)

def listimages():
    '''Print out all images including base images in account'''
    cs = auth()
    fields = ['Name', 'Status', 'Created at', 'ID']
    data = []
    for image in cs.images.list():
        data.append((image.name, image.status, image.created, image.id))
    printhortable(fields, data)

def cloneserver(*args, **kwargs):
    '''This function will automatically create an image and a server from that
    image that is the same size as the original or larger. origserver param
    can be a uuid or name(case sensitive).'''
    cs = auth(kwargs['region'])
    orig = kwargs['orig']
    for svr in cs.servers.list():
        if orig == server.name or orig == server.id:
            orig = cs.servers.get(svr.id)
    size = kwargs['size']
    for flvr in cs.flavors.list():
        if size == int(flvr.ram):
            flavor = flvr.id
    if flavor < int(orig.flavor['id']):
        print 'The original server is larger than the new server.'
        exit(1)
    else:
        if not kwargs['imagename']:
            imagename = '%s_%s' % (server.name,
                    str(pyrax.utils.datetime.date.today()))
        else:
            imagename = kwargs['imagename']
        printvertable([('Name:', imagename), ('Server:', server.name)])
        build = raw_input('Is this information correct for the image? (y|n) ')
        if build.lower() == 'y':
            del build
            image = cs.images.get(cs.servers.create_image(server.id, imagename))
            pyrax.utils.wait_until(image, 'status', ['ACTIVE', 'ERROR'],
                    attempts=0, verbose=True)
            if kwargs['clonename'] is None:
                clonename = server.name + '-clone'
            else:
                clonename = kwargs['clonename']
            printvertable([('Name', clonename), ('Size', size))])
            build = raw_input('Is this information correct for the build? (y|n) ')
            if build.lower() == 'y':
                clone = cs.servers.create(clonename, image.id, size)
                pyrax.utils.wait_until(clone, 'status', ['ACTIVE', 'ERROR'],
                attempts=0, verbose=True)
                printvertable([('Name', clone.name),
                        ('Pass', clone.adminPass), ('Status', clone.status),
                        ('IP', clone.networks)])
            else:
                exit(0)
        else:
            exit(0)


def exit(stat):
    print 'Exiting...'
    pyrax.utils.sys.exit(stat)

def main():
    '''Parse all CLI arguments.'''
    parser = argparse.ArgumentParser(description='''By default and with no 
    arguments, this script will build 3 servers with 512 MB of RAM named 
    web1-3.''')
    parser.add_argument('--list-servers', action='store_true',
            help='List servers in account.')
    parser.add_argument('--list-images', action='store_true',
            help='List images in account.')
    parser.add_argument('-o', '--original-server', metavar='NAME|ID', type=str,
            action='store', help='Name to use for server.')
    parser.add_argument('-c', '--clone-name', metavar='NAME', type=str,
    action='store', help='Name to use for server.')
    parser.add_argument('-s', '--size', metavar='SIZE', type=int,
            action='store',
            choices=['512', '1024', '2048', '4096', '8192', '15360', '30720'],
            default=512
            help='Size to build clone in MB.')
    parser.add_argument('-i', '--image', metavar='NAME', type=str,
            action='store', help='Name to use for image.')
    parser.add_argument('-r', '--region', metavar='REGION', type=str,
            action=store, help='Region to build server in')
    args = parser.parse_args()

    if args.list_servers:
        listservers()
    elif args.list_images:
        listimages()
    else:
        cloneserver(orig=args.name, size=args.size, imagename=args.image,
            region=args.region)

if __name__ == '__main__':
    main()
