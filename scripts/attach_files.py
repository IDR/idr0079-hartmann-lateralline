import argparse
import omero.clients
import omero.cli
import sys
from omero_upload import upload_ln_s
from pathlib import Path

# In-place Attach zip file to dataset

MIMETYPE = 'application/zip'
NAMESPACE = 'openmicroscopy.org/idr/analysis/original'
OMERO_DATA_DIR = '/data/OMERO'
DRY_RUN = True

def main(conn, filepath):
  path = Path(filepath)
  filename = path.name
  if path.suffix != 'zip':
    sys.exit("Not a zip file")

  ds_name = path.stem
  tmp = conn.getObjects("Dataset", attributes={"name": ds_name})
  if len(tmp) > 1:
    sys.exit("More than one dataset found")
  tgt = tmp[0]

  existingfas = set(
    a.getFile().name for a in tgt.listAnnotations()
    if isinstance(a, omero.gateway.FileAnnotationWrapper))
  if filename in existingfas:
    sys.exit("File already attached.")

  print("Attaching {} to Dataset {} [{}]".format(path.resolve(), tgt.getName(), tgt.getId()))
  if not DRY_RUN:
    fo = upload_ln_s(conn.c, path.resolve(), OMERO_DATA_DIR, MIMETYPE)
    fa = omero.model.FileAnnotationI()
    fa.setFile(fo._obj)
    fa.setNs(omero.rtypes.rstring(NAMESPACE))
    fa = conn.getUpdateService().saveAndReturnObject(fa)
    fa = omero.gateway.FileAnnotationWrapper(conn, fa)
    tgt.linkAnnotation(fa)


if __name__ == '__main__':
  parser = argparse.ArgumentParser()
  parser.add_argument("file", help="The file to attach.")

  args = parser.parse_args()

  with omero.cli.cli_login() as c:
    conn = omero.gateway.BlitzGateway(client_obj=c.get_client())
    main(conn, args.file)
