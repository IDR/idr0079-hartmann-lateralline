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

base_tables_path = os.path.join(
    os.getcwd(),
    "experimentA/idr0079_experimentA_extracted_measurements/%s/",
    "%s"
)

def get_omero_col_type(dtype):
    """Returns s for string, d for double, l for long/int"""
    if dtype == "int":
        return "l"
    elif dtype == "float":
        return "d"
    return "s"


def populate_metadata(image, csv_name, table_name):

    client = image._conn.c
    ctx = ParsingContext(
        client, image._obj, file=csv_name, allow_nan=True,
        table_name=table_name
    )
    ctx.parse()


def process_image(conn, image, table_name):
    # Read csv for each image
    image_name = image.name
    table_pth = base_tables_path % (image_name, image_name)
    table_pth += table_name
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
    roi_count = len(result.rois)
    row_count = len(df.index)
    print("Found %s ROIS and %s csv rows" % (roi_count, row_count))
    if roi_count != row_count:
        return f"Mismatching counts: {table_pth}"

    # Go through every row, find Shape ID and ROI ID
    # for row in df.to_dict(orient='records'):
    for index, row in df.iterrows():
        # print("ROW", index, "/", len(result.rois))
        roi = result.rois[index]
        new_row = {}
        # Create a copy of row, with columns named with_underscores (no spaces)
        for c in col_names:
            value = row[c]
            new_row[c.replace(" ", "_")] = value
        new_row["Roi"] = roi.id.val
        df2 = df2.append(new_row, ignore_index=True)

    csv_name = image.name + ".csv"
    print("writing", csv_name)
    with open(csv_name, "w") as csv_out:
        csv_out.write("# header roi," + ",".join(col_types) + "\n")

    df2.to_csv(csv_name, mode="a", index=False)

    print("populate metadata...")
    bulk_name = table_name.lstrip("_").replace(".tsv", "")
    populate_metadata(image, csv_name, bulk_name)
    # delete csv
    os.remove(csv_name)


def main(conn, args):

    project = conn.getObject("Project", attributes={"name": project_name})
    print("Project", project.id)
    conn.SERVICE_OPTS.setOmeroGroup(project.getDetails().group.id.val)
    # For each Image in Project, open the local CSV by name...
    table_names = args.table_names.split(",")
    errors = []
    ok = 0
    for table_name in table_names:
        print(f"\n\nProcessing table: {table_name}")
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
                msg = process_image(conn, image, table_name)
                if msg is not None:
                    errors.append(msg)
                else:
                    ok += 1
    print("Successfully attached %s tables to images" % ok)
    print("\n".join(errors))


if __name__ == "__main__":
    # NB: Assumes that the segmentation ROIs are added to the image
    # (and *before* any other ROIs)
    #
    # USAGE: (use --name if you want to ONLY process 1 image)
    # Comma-separated table names
    # $ cd idr0079-hartmann-lateralline
    # $ python scripts/csv_to_roi_table.py --name 00E41C184C _pea3smFISH_RNAcounts_predicted.tsv,_archetype_TFOR_classifications.tsv
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", help="Filter images by Name")
    parser.add_argument("table_names",
        help="comma-separated list of table names",
        default="_other_measurements.tsv")
    args = parser.parse_args()

    with omero.cli.cli_login() as c:
        conn = omero.gateway.BlitzGateway(client_obj=c.get_client())
        main(conn, args)
        conn.close()
