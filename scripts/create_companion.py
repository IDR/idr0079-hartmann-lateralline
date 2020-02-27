from pathlib import Path
import os
import uuid


template = """<?xml version='1.0' encoding='utf-8'?>
<OME xmlns="http://www.openmicroscopy.org/Schemas/OME/2016-06" xmlns:OME="http://www.openmicroscopy.org/Schemas/OME/2016-06" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.openmicroscopy.org/Schemas/OME/2016-06 http://www.openmicroscopy.org/Schemas/OME/2016-06/ome.xsd">
  <Image ID="Image:0" Name="{}">
    <Pixels DimensionOrder="XYZCT" ID="Pixels:0:0" SizeC="1" SizeT="1" SizeX="{}" SizeY="{}" SizeZ="{}" Type="uint16">
      <TiffData FirstC="0" FirstT="0" FirstZ="0" PlaneCount="{}">
        <UUID FileName="{}">urn:uuid:{}</UUID>
      </TiffData>
    </Pixels>
  </Image>
</OME>
"""

#in_dir = Path("/uod/idr/filesets/idr0079-hartmann-lateralline/20200220-ftp")
#out_dir = Path("home/dlindner/generated")
in_dir = Path("/Users/dlindner/idr0079_mount")
out_dir = Path("/Users/dlindner/generated")
nfs_dir = Path("/uod/idr/filesets/idr0079-hartmann-lateralline/20200220-ftp")


def get_xyz(image_file):
  stream = os.popen("tiffinfo {} | grep \"Image Width\" | tail -1".format(image_file))
  output = stream.read().split()
  x = int(output[2])
  y = int(output[5])
  stream = os.popen("tiffinfo {} | grep \"images\" | tail -1".format(image_file))
  output = stream.read().split("=")
  z = int(output[1])
  return x, y, z

def write_companion(exp_dir, img_dir, file_name, x, y, z, uuid):
  output = template.format(file_name, x, y, z, z, file_name, uuid)
  p = out_dir / exp_dir / img_dir
  p.mkdir(parents=True, exist_ok=True)
  out_file = p / "{}.companion.ome".format(file_name)
  writer = open(out_file, "w")
  writer.write(output)
  writer.close()
  ln = nfs_dir / exp_dir / img_dir / file_name
  os.system("ln -s {} {}".format(str(ln), str(p.resolve())))


for exp_dir in in_dir.iterdir():
  for img_dir in exp_dir.iterdir():
    for img_file in img_dir.iterdir():
      if "_seg." in img_file.name:
        file_name = img_file.name
        img_dir_name = img_dir.name
        exp_dir_name = exp_dir.name
        x, y, z = get_xyz(str(img_file.resolve()))
        write_companion(exp_dir_name, img_dir_name, file_name, x, y ,z, str(uuid.uuid1()))

