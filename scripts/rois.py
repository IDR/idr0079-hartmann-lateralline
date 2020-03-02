#!/usr/bin/env python

# Based on Simon's script
# https://raw.githubusercontent.com/IDR/idr0052-walther-condensinmap/master/scripts/upload_and_create_rois.py

import os
import omero.clients
from omero.gateway import BlitzGateway
from omero_rois import masks_from_label_image

PROJECT = "idr0079-hartmann-lateralline/experimentA"
RGBA = (255, 255, 255, 128)
DRYRUN = False

def create_rois(im, seg_im):
    assert im.getSizeZ() == seg_im.getSizeZ()
    rois = []
    for z in range(0, im.getSizeZ()):
        plane = seg_im.getPrimaryPixels().getPlane(z, 0, 0)
        roi = omero.model.RoiI()
        shapes = masks_from_label_image(plane, rgba=RGBA, z=z, raise_on_no_mask=False)
        if len(shapes) > 0:
            print("z={}, shapes={}".format(z, len(shapes)))
            for s in shapes:
                roi.addShape(s)
            rois.append(roi)
    return rois


def save_rois(conn, im, rois):
    print('Saving %d ROIs for image %d:%s' % (len(rois), im.id, im.name))
    us = conn.getUpdateService()
    for roi in rois:
        # Due to a bug need to reload the image for each ROI
        im = conn.getObject('Image', im.id)
        roi.setImage(im._obj)
        roi1 = us.saveAndReturnObject(roi)
        assert roi1


def get_images(conn):
    project = conn.getObject('Project', attributes={'name': PROJECT})
    for dataset in project.listChildren():
        for image in dataset.listChildren():
            if image.name.endswith('companion.ome'):
                continue
            yield image


def get_segmented_image(conn, image):
    name = image.name.replace(".tif", "")
    name = name+"_seg.tif.companion.ome"
    result = conn.getObject('Image', attributes={'name': name})
    assert result
    return result


def main(conn):
    for im in get_images(conn):
        print('Image: {}'.format(im.id))
        seg_im = get_segmented_image(conn, im)
        print('Segmented Image: {}'.format(seg_im.id))
        rois = create_rois(im, seg_im)
        if not DRYRUN:
            save_rois(conn, im, rois)


if __name__ == '__main__':
    host = os.environ.get('OMERO_HOST', 'localhost')
    port = os.environ.get('OMERO_PORT', '4064')
    user = os.environ.get('OMERO_USER', 'NA')
    pw = os.environ.get('OMERO_PASSWORD', 'NA')
    with BlitzGateway(user, pw, host=host, port=port) as conn:
        main(conn)


