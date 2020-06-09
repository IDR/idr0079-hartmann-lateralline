import csv
import sys

# Image names have to be unique, so have to  add '_seg'
# to the images in the xyz_seg datasets

file = sys.argv[1]

with open(file+"_mod", mode='w') as out_file:
    csv_writer = csv.writer(out_file, delimiter=',')
    with open(file) as in_file:
        csv_reader = csv.reader(in_file, delimiter=',')
        for row in csv_reader:
            if row[0].endswith("_seg"):
                row[1] += "_seg"
            csv_writer.writerow(row)
