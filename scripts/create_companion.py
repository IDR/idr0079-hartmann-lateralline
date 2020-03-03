from pathlib import Path
import os
import uuid


template_1c = """<?xml version='1.0' encoding='utf-8'?>
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

template_2c = """<?xml version='1.0' encoding='utf-8'?>
<OME xmlns="http://www.openmicroscopy.org/Schemas/OME/2016-06" xmlns:OME="http://www.openmicroscopy.org/Schemas/OME/2016-06" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.openmicroscopy.org/Schemas/OME/2016-06 http://www.openmicroscopy.org/Schemas/OME/2016-06/ome.xsd">
  <Image ID="Image:0" Name="{}">
    <Pixels DimensionOrder="XYZCT" ID="Pixels:0:0" SizeC="2" SizeT="1" SizeX="{}" SizeY="{}" SizeZ="{}" Type="uint16">
      <TiffData FirstC="0" FirstT="0" FirstZ="0" PlaneCount="{}">
        <UUID FileName="{}">urn:uuid:{}</UUID>
      </TiffData>
      <TiffData FirstC="1" FirstT="0" FirstZ="0" PlaneCount="{}">
        <UUID FileName="{}">urn:uuid:{}</UUID>
      </TiffData>
    </Pixels>
  </Image>
</OME>
"""

# sshfs -oro idr-testing-omero:/uod/idr/filesets/idr0079-hartmann-lateralline/20200220-ftp idr0079_mount
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

def write_companions(exp_dir, img_dir, file_name, file_name_2, seg_file_name, x, y, z):
  # generate companion file for image(s):
  img_name = img_dir.name
  if file_name_2 is None:
    output = template_1c.format(img_name, x, y, z, z, file_name, str(uuid.uuid1()))
  else:
    output = template_2c.format(img_name, x, y, z, z, file_name, str(uuid.uuid1()), z, file_name_2, str(uuid.uuid1()))
  p = out_dir / exp_dir.name / img_dir.name
  p.mkdir(parents=True, exist_ok=True)
  out_file = p / "{}.companion.ome".format(img_name)
  writer = open(out_file, "w")
  writer.write(output)
  writer.close()
  
  # link image(s):
  ln = nfs_dir / exp_dir.name / img_dir.name / file_name
  os.system("ln -s {} {}".format(str(ln), str(p.resolve())))
  if file_name_2 is not None:
    ln = nfs_dir / exp_dir / img_dir / file_name_2
    os.system("ln -s {} {}".format(str(ln), str(p.resolve())))

  # generate companion file for segmented image:
  seg_name = "{}_seg".format(img_name)
  output = template_1c.format(seg_name, x, y, z, z, seg_file_name, str(uuid.uuid1()))
  out_file = p / "{}.companion.ome".format(seg_name)
  writer = open(out_file, "w")
  writer.write(output)
  writer.close()

  # link segmented image:
  ln = nfs_dir / exp_dir.name / img_dir.name / seg_file_name
  os.system("ln -s {} {}".format(str(ln), str(p.resolve())))


def proc_img_dir(exp_dir, img_dir, files):
  img_file = None
  img_file_2 = None
  seg_file = None
  for f in files:
    if f.name.endswith("_seg.tif"):
      seg_file = f
    elif img_file is None:
      img_file = f
    elif img_file_2 is None:
      img_file_2 = f
  x, y, z = get_xyz(str(img_file.resolve()))
  write_companions(exp_dir, img_dir, img_file.name, img_file_2.name if img_file_2 else None, seg_file.name, x, y ,z)


for exp_dir in in_dir.iterdir():
  for img_dir in exp_dir.iterdir():
    files = [x for x in img_dir.iterdir()]
    proc_img_dir(exp_dir, img_dir, files)

