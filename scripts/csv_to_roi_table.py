#!/usr/bin/env python

import pandas
import argparse
import csv
import mimetypes

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


def set_name_for_all_rois(conn, image_id):
    params = omero.sys.ParametersI()
    params.addId(image_id)
    query = """select roi from Roi as roi
            where roi.image.id = :id"""
    rois = conn.getQueryService().findAllByQuery(query, params, conn.SERVICE_OPTS)
    for roi in rois:
        if roi.name is None:
            roi.name = rstring(str(roi.id.val))
    conn.getUpdateService().saveArray(rois)


def process_image(conn, image):
    # Since populate_metadata fails if rois don't have name
    set_name_for_all_rois(conn, image.id)

    # Read csv for each image
    image_name = image.name

    table_pth = tables_path % (image_name, image_name)
    print('table_pth', table_pth)
    df = pandas.read_csv(table_pth, delimiter="\t")

    col_types = [get_omero_col_type(t) for t in df.dtypes]
    col_names = list(df.columns)
    new_col_names = [name.replace(" ", "_") for name in col_names]
    # Create output table with extra columns
    df2 = pandas.DataFrame(columns=(["Roi"] + new_col_names))

    # Get all ROIs - The order seems to correspond to the order they were
    # created in, which matches the order of rows in the .tsv
    result = conn.getRoiService().findByImage(image.id, None)

    # Go through every row, find Shape ID and ROI ID
    # for row in df.to_dict(orient='records'):
    for index, row in df.iterrows():
        roi = result.rois[index]
        print("ROW", index, roi.id.val)
        new_row = {}
        # Create a copy of row, with columns named with_underscores (no spaces)
        for c in col_names:
            value = row[c]
            new_row[c.replace(" ", "_")] = value
        new_row["Roi"] = roi.id.val
        df2 = df2.append(new_row, ignore_index=True)
        # all ROIs must have a name for populate metadata
        roi.name = rstring(row["Cell ID"])
        conn.getUpdateService().saveObject(roi)

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
    # NB: Assumes that the segmentation ROIs are added to the image
    # (and *before* any other ROIs)
    #
    # USAGE: (use --name if you want to ONLY process 1 image)
    # $ cd idr0079-hartmann-lateralline
    # $ python scripts/csv_to_roi_table --name 00E41C184C
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", help="Filter images by Name")
    args = parser.parse_args()

    with omero.cli.cli_login() as c:
        conn = omero.gateway.BlitzGateway(client_obj=c.get_client())
        main(conn, args)
        conn.close()
