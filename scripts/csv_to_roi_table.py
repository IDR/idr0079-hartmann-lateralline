#!/usr/bin/env python

import pandas
import argparse
import csv
import mimetypes
from shapely.geometry import Polygon, Point

import omero.clients
import omero.cli
import omero
from omero.rtypes import rint, rdouble, rstring
from omero_metadata.populate import ParsingContext
from omero.util.metadata_utils import NSBULKANNOTATIONSRAW
import os 

project_name = "idr0079-hartmann-lateralline/experimentA"

tables_path = os.path.join(
    os.getcwd(),
    "experimentA/idr0079_experimentA_extracted_measurements/%s/",
    "%s_other_measurements.tsv"
)
print("tables_path", tables_path)


def get_omero_col_type(dtype):
    """Returns s for string, d for double, l for long/int"""
    if dtype == "int":
        return "l"
    elif dtype == "float":
        return "d"
    return "s"


def populate_metadata(image, csv_name):

    mt = mimetypes.guess_type(csv_name, strict=False)[0]
    fileann = conn.createFileAnnfromLocalFile(
        csv_name, mimetype=mt, ns=NSBULKANNOTATIONSRAW
    )
    fileid = fileann.getFile().getId()
    image.linkAnnotation(fileann)
    client = image._conn.c
    ctx = ParsingContext(
        client, image._obj, fileid=fileid, file=csv_name, allow_nan=True
    )
    ctx.parse()


def get_shapes_at_point(conn, image_id, x, y, z):

    # Get all shapes that contain the point
    params = omero.sys.ParametersI()
    params.addId(image_id)
    params.add('theZ', rint(z))
    # params.add('x', rdouble(x_pixels))
    # params.add('y', rdouble(y_pixels))
    query = """select shape from Shape as shape
            join shape.roi as roi
            where roi.image.id = :id
            and shape.theZ = :theZ"""
    # for mask
    #         and shape.x < :x
    #         and shape.y < :y
    #         and (shape.width + shape.x) > :x"""

    shapes = conn.getQueryService().findAllByQuery(query, params, conn.SERVICE_OPTS)

    shapes_at_point = []
    for shape in shapes:
        if isinstance(shape, omero.model.PolygonI):
            points = shape.points.val
            xy = []
            for p in points.split(" "):
                xy.append([float(c) for c in p.strip(",").split(",")])
            if len(xy) > 3 and Polygon(xy).contains(Point(x, y)):
                shapes_at_point.append(shape)

    return shapes_at_point


def get_shape_ids(conn, roi_id):
    params = omero.sys.ParametersI()
    params.addId(roi_id)
    query = """select shape from Shape as shape
            where shape.roi.id = :id"""
    shapes = conn.getQueryService().findAllByQuery(query, params, conn.SERVICE_OPTS)
    return [s.id.val for s in shapes]


def set_name_for_all_rois(conn, image_id):
    params = omero.sys.ParametersI()
    params.addId(image_id)
    query = """select roi from Roi as roi
            where roi.image.id = :id"""
    rois = conn.getQueryService().findAllByQuery(query, params, conn.SERVICE_OPTS)
    for roi in rois:
        roi.name = rstring(str(roi.id.val))
    conn.getUpdateService().saveArray(rois)


def process_image(conn, image):
    # Since populate_metadata fails if rois don't have name
    set_name_for_all_rois(conn, image.id)

    # Read csv for each image
    image_name = image.name
    pix_x = image.getPixelSizeX()   # 0.09
    pix_y = image.getPixelSizeY()   # 0.09
    pix_z = image.getPixelSizeZ()   # 0.19
    print(pix_x, pix_y, pix_z)
    # hard-coded values that seem to work better
    pix_x = 0.1
    pix_y = 0.1
    pix_z = 0.23
    print(pix_x, pix_y, pix_z)

    table_pth = tables_path % (image_name, image_name)
    print('table_pth', table_pth)
    df = pandas.read_csv(table_pth, delimiter="\t")

    col_types = [get_omero_col_type(t) for t in df.dtypes]
    col_names = list(df.columns)
    new_col_names = [name.replace(" ", "_") for name in col_names]
    # Create output table with extra columns
    df2 = pandas.DataFrame(columns=(["Roi", "Shape"] + new_col_names))

    # Go through every row, find Shape ID and ROI ID
    # for row in df.to_dict(orient='records'):
    for index, row in df.iterrows():
        x_raw = row["Centroids RAW X"]
        y_raw = row["Centroids RAW Y"]
        z_raw = row["Centroids RAW Z"]
        x_pixels = x_raw / pix_x
        y_pixels = y_raw / pix_y
        z_index = int(round(z_raw / pix_z))

        polygons = get_shapes_at_point(conn, image.id, x_pixels, y_pixels, z_index)
        if len(polygons) == 1:
            poly = polygons[0]
            print("Found 1 polygon. ID:", poly.id.val)
            roi = poly.roi
            new_row = {}
            # Create a copy of row, with columns named with_underscores (no spaces)
            for c in col_names:
                value = row[c]
                new_row[c.replace(" ", "_")] = value
            new_row["Roi"] = roi.id.val
            for shape_id in get_shape_ids(conn, roi.id.val):
                new_row["Shape"] = shape_id
                df2 = df2.append(new_row, ignore_index=True)
            # all ROIs must have a name for populate metadata
            roi.name = rstring(row["Cell ID"])
            conn.getUpdateService().saveObject(roi)
        else:
            print(" - found polygons:", len(polygons))

    csv_name = image.name + ".csv"
    print("writing", csv_name)
    with open(csv_name, "w") as csv_out:
        csv_out.write("# header roi,l," + ",".join(col_types) + "\n")

    df2.to_csv(csv_name, mode="a", index=False)

    print("populate metadata...")
    populate_metadata(image, csv_name)


def main(conn, args):

    project = conn.getObject("Project", attributes={"name": project_name})
    print("Project", project.id)
    conn.SERVICE_OPTS.setOmeroGroup(project.getDetails().group.id.val)
    # For each Image in Project, open the local CSV and summarise to one row
    for dataset in project.listChildren():
        for image in dataset.listChildren():
            # ignore _seg images etc.
            if '_' in image.name:
                continue
            if args.name and image.name != args.name:
                continue
            if image.getROICount() == 0:
                print("No ROIs for image", image.name)
                continue
            process_image(conn, image)


if __name__ == "__main__":
    # USAGE:
    # $ cd idr0079-hartmann-lateralline
    # $ python csv_to_roi_table --name 00E41C184C
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", help="Filter images by Name")
    args = parser.parse_args()

    with omero.cli.cli_login() as c:
        conn = omero.gateway.BlitzGateway(client_obj=c.get_client())
        main(conn, args)
        conn.close()
