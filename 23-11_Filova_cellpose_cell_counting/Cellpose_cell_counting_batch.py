#load all libraries necessary

import os
from cellpose import utils, io, models
import matplotlib.pyplot as plt
import numpy as np

# change directory to the one where files are saved

os.chdir('C:/Users/sveco/Documents/IEM_microscopy/Cellpose/test/')

# create list with all filenames (can be adjusted)

files = os.listdir()

# set parameters based on tested settings from Cellpose GUI

model_type = 'cyto'
channels = [2,1]

# run model on all files

model = models.Cellpose(gpu=False,model_type=model_type)

imgs = [io.imread(filename).astype('uint8') for filename in files]
masks, flows, styles, diams = model.eval(imgs, diameter=None, channels=channels)    # diameter=None should adjust diameter for each file
io.masks_flows_to_seg(imgs, masks, flows, diams, files, channels)
io.save_to_png(imgs, masks, flows, files)

# find number of ROIs and save it to csv file

csv_file = open('cellpose_roi_counts.csv','w')
for i in range(len(files)):
    num_roi = np.max(masks[i])
    csv_file.write(f'{files[i]},{num_roi} \n')
csv_file.close()