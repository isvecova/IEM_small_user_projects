#people/IEM/BarboraVoltrova #imageAnalysis #IEMprojects/2026 

# Goal 
Quantify green signal in cells grown on titanium material. 

# Dataset
- z-stack .ims images (16-bit) from Andor BC43 containing 3 channels
	- channel 1 contains red signal from actin - usually quite nice
	- channel 2 contains green signal that is supposed to be quantified - should be overlapping with the actin signal
	- channel 3 contains DAPI

# Discussion 
During the initial meeting, we discussed how to measure the green signal from the cells grown on a titanium material. 
The initial idea was to quantify the total green intensity and divide it by the number of nuclei. Nuclei segmentation could be done using StarDist. The problem with this approach is that there might be an unspecific signal outside of the cells, that will be included in the measurements. 
To avoid that, we decided to instead segment the area with cells using the actin channel, and then measure mean signal intensity only in these regions. 

# Scripts
- an ImageJ macros for batch segmentation and signal measurement
	- **260504_signal_in_cells_threshold_list.ijm** - sequentially tries multiple thresholds from a user-defined list one-by-one, measurements for each threshold are stored in a new folder
	- **260504_signal_in_cells_single_threshold.ijm** - does the same thing, but only with a single threshold

## How to use
The output is an ImageJ macro, that is run in Fiji. 
Fiji can be installed from here: https://imagej.net/software/fiji/downloads

Since the macro works with 3D images, it also requires the **3D ImageJ Suite** plugin. 
For installation, follow the steps here: https://mcib3d.frama.io/3d-suite-imagej/#installation
Macro inspiration from: https://mcib3d.frama.io/3d-suite-imagej/plugins/3DManager/3D-Manager-macros/

To check that **3D ImageJ Suite** has been successfully installed, go to the Plugins menu. You should see 3DSuite listed.

![Intensity measurements](images\3DImageJSuite_installed.png)

When the plugin is installed, the macro can be opened by drag-and-drop to the Fiji toolbar and run by pressing the Run button in Macro editor. 
After pressing Run, the macro will ask for a folder containing the images. Then, it will process all the .ims images in that folder and save results table, as well as z-projected signal (cyan) and actin (magenta) images overlayed with the segmented region as yellow outline.

**In the current output, the measurements are raw intensities. To subtract the background, it is enough to just subtract 100 (background value) from all the mean signal measurements.**

## Analysis steps

For each threshold value in `threshold_list`, the macro processes all `.ims` images in the selected folder.

For each image:

1.  Open the `.ims` image using Bio-Formats, specifically `series_1` (original data without downsampling).
2.  Check that the image has exactly 3 channels. If not, skip the image.
3.  Duplicate the actin channel.
4.  Apply 3D median filtering to the actin channel. This is done to remove noise and smooth out the mask.
5.  Segment the filtered actin channel using fixed-threshold 3D Simple Segmentation from 3D ImageJ Suite.
6.  Store the segmented foreground mask as a 3D ROI/object in 3D Manager.
7.  Measure the volume of the segmented actin-positive region.
8.  Duplicate the signal channel.
9.  Measure mean and standard deviation of the signal channel inside the actin-positive 3D mask.
10. Measure mean and standard deviation of the actin channel inside the same mask as a control.
11. Measure mean and standard deviation of the binary mask inside the same mask as a segmentation control.
12. Extract sample information from the filename by splitting it at underscores:
    -   first part → `sampleType`
    -   second part → `sampleReplicate`
13. Store all measurements in the ImageJ Results table.
14. Create maximum-intensity z-projections of:
    -   actin channel
    -   signal channel
    -   binary mask
15. Convert actin and signal projections to 8-bit images using fixed display ranges.
16. Detect mask outlines from the projected binary mask.
17. Merge the projected signal and actin channels:
    -   signal shown in cyan
    -   actin shown in magenta
18. Overlay the mask outline and flatten the image.
19. Save the merged quality-control image as `.png`.
20. Close all images and reset 3D Manager and ROI Manager.

At the end of processing for each threshold, the Results table is saved as `measurements.csv` in the corresponding threshold output folder.

------------------------------------------------------------------------

## Default parameters

    actinChannel = 1
    signalChannel = 2
    threshold_list = [130, 140, 150]

### Segmentation parameters

    3D median filter:
    x = 2
    y = 2
    z = 2
	*Values can be increased if the masks are too noisy. Alternatively, a Gaussian filter can be used instead.
	The data analyzed were obtained with 20x and 2x2 binning (voxel size ~0.6 um). Filter size has to be adjusted if this changes.*

    3D Simple Segmentation (from the 3D ImageJ Suite plugin):
    seeds = None
    low_threshold = current threshold from threshold_list
    min_size = 0
    max_size = -1

### Measurement parameters

The 3D Manager is configured to measure:

    volume
    mean_grey_value
    std_dev_grey_value

Measured outputs:

    image
    sampleType
    sampleReplicate
    volume
    signalMean
    signalStd

    For control only: 
    actinMean
    actinStd
    binMean
    binStd

### Display parameters for QC images

    Actin projection display range:
    min = 100
    max = 1000

    Signal projection display range:
    min = 100
    max = 500

### Output files

For each threshold, the macro creates:

    output130/
    output140/
    output150/

Each output folder contains:

    measurements.csv
    mergedMask_<imageName>.png

------------------------------------------------------------------------

## Assumptions

1.  Input images are `.ims` files.
4.  Each image has exactly 3 channels.
5.  Channel 1 contains actin by default.
6.  Channel 2 contains the signal to be quantified by default.
7.  Actin-positive regions correspond to cells or regions of interest, that overlap with the quantified signal.
8.  A fixed threshold is appropriate for segmenting the actin channel.
10. Objects are not separated into biologically distinct cells, we just care about the total are.
11. The filename contains at least two underscore-separated parts, that correspond to the sample identification:
    -   `sampleType_sampleReplicate_...`
12. The 3D ImageJ Suite plugin is installed.
13. The projected QC image is for visual inspection only; measurements are performed in 3D before z-projection.

------------------------------------------------------------------------

# Output
![Intensity measurements](images\intensity_measurements_scatter_plot.png)

# Time breakdown
| Date | Time | Duration (h) | Activity |
|----------|----------|----------|----------|
| 4.5.2026 | 10:00-11:00 | 1 | Initial discussion |
| 4.5.2026 | 16:50-18:50 | 2 | Macro writing, testing segmentation strategies |
| 4.5.2026 | 18:50-19:20 | 1.5 | Running macro, testing, optimizing output and fixing bugs |
| 5.5.2026 | 09:15-10:45 | 1.5 | Checking output, documenting the pipeline |

# Author and acknowledgement
Written by: Iva Švecová (iva.svecova@iem.cas.cz)

Date: 4.5.2026 

If you use the script for a publication, please cite ImageJ and 3D ImageJ Suite plugin. 

Remember:
All publications resulting from the use of instruments and support staff within the MSC IEM facility should acknowledge the facility, and the facility should be informed of the publication.
Assistance provided above the technical or routine level, with any facility staff providing scientific input and expertise in experimental set-up, acquisition, analysis or writing, should be recognized through co-authorship on resulting publications. Please discuss authorship and acknowledgement with facility staff prior to manuscript submission.
More information here: https://www.iem.cas.cz/en/department/microscopy-service-centre/#acknowledgement


