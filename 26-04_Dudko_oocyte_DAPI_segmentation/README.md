#people/IEM/NataliiaDudko #imageAnalysis #IEMprojects/2026 

260412: 20.30-23.00
# Goal 
Measure signal in one channel in the area overlapping with the DAPI channel. 

# Dataset
- z-stack .czi images (8-bit) containing 3 channels
	- assumed that channel 2 is the DAPI channel and channel 3 contains signal for measurement

# Output
- an ImageJ macro (fixedThresholdSegmentation.ijm) for batch segmentation and signal measurement
## Analysis steps
For each image: 
1. Open using BioFormats.
2. Duplicate the DAPI channel (number can be set up, by default the 2nd).
3. Apply median filtering for noise removal (anisotropic; works ok also without).
4. Apply thresholding with fixed value using the 3D ImageJ Suite Simple segmentation function. 
5. Store the positive ROI to 3D manager. 
6. Measure the ROI area. 
7. Duplicate the channel with signal (value can be set up, by default the 3rd).
8. Measure mean and std of the signal in this channel overlapping with the DAPI positive area. 
9. Store measurements to the results table. 
10. Merge the DAPI and the mask channel together and store it for future reference as .tif.
11. Close all the images.
At the end of the loop, store the results table. 

## How to use
The output is an ImageJ macro. Open it by Drag-and-drop on Fiji installation of ImageJ. 
Fiji can be installed from here: https://imagej.net/software/fiji/downloads

Since the macro works with 3D images, it also requires the **3D ImageJ Suite** plugin. 
For installation, follow the steps here: https://mcib3d.frama.io/3d-suite-imagej/#installation
Macro inspiration from: https://mcib3d.frama.io/3d-suite-imagej/plugins/3DManager/3D-Manager-macros/

When the plugin is installed, the macro can be run by pressing the Run button in Macro editor. 
After pressing Run, the macro will ask for a folder containing the images. Then, it will process all the .czi images in that folder and save results table, as well as the saved masks with DAPI channel in the 'output' folder within the folder with data. 

# Potential problems and limitations
Of the macro: 
- at the moment, the macro uses fixed threshold, as 3D ImageJ Suite does not support automatic thresholding using Otsu or similar algorithm
	- it is necessary to test the macro and evaluate the quality of the segmentation
	- the alternative option is to apply an auto-threshold for example on a selected plane, or to find another way how to implement it (or to implement the analysis in Python instead)
- it is assumed that the 2nd channel is DAPI and the 3rd channel contains signal (can be adjusted)
Of the dataset: 
- in the testing images, the DAPI channel contains some oversaturated area - this can be a problem when looking for threshold
- the images are 8-bit, which is not very suitable for quantification - for future acquisitions, it is advisable to use 16-bit instead

# Time breakdown
Macro writing and testing: 2h
Documentation: 0.5 h

# Author and acknowledgement
Written by: Iva Švecová (iva.svecova@iem.cas.cz)
Date: 12.4.2026 

If you use the script for a publication, please cite ImageJ and 3D ImageJ Suite plugin. 

Remember:
All publications resulting from the use of instruments and support staff within the MSC IEM facility should acknowledge the facility, and the facility should be informed of the publication.
Assistance provided above the technical or routine level, with any facility staff providing scientific input and expertise in experimental set-up, acquisition, analysis or writing, should be recognized through co-authorship on resulting publications. Please discuss authorship and acknowledgement with facility staff prior to manuscript submission.
More information here: https://www.iem.cas.cz/en/department/microscopy-service-centre/#acknowledgement


