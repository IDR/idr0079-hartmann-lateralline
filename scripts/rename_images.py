import os
import omero.clients
from omero.gateway import BlitzGateway

# Just removes the .companion.ome extensions

PROJECT = "idr0079-hartmann-lateralline/experimentA"
DRYRUN = True

def get_images(conn):
    project = conn.getObject('Project', attributes={'name': PROJECT})
    for dataset in project.listChildren():
        for image in dataset.listChildren():
            yield image

def main(conn):
    us = conn.getUpdateService()
    for im in get_images(conn):
        ren = im.getName().replace(".companion.ome", "")
        print("Rename {} to {}".format(im.getName(), ren))
        if not DRYRUN:
            im.setName(ren)
            im.save()

if __name__ == '__main__':
    host = os.environ.get('OMERO_HOST', 'localhost')
    port = os.environ.get('OMERO_PORT', '4064')
    user = os.environ.get('OMERO_USER', 'NA')
    pw = os.environ.get('OMERO_PASSWORD', 'NA')
    with BlitzGateway(user, pw, host=host, port=port) as conn:
        main(conn)
