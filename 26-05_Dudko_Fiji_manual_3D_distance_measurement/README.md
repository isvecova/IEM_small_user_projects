# Manual 3D distance measurement in Fiji

## Goal

Support manual distance measurements between two 3D marks or objects using Fiji's 3D Manager.

The idea is to generate an empty image with the same size as the data, and draw a point using the Pencil tool to the desired places (such as the two ends of the mitotic spindle). The distance between these manually drawn points can then be measured. 

## Input and output

Use an image stack with known X/Y/Z calibration and a label image containing the objects or marks to compare. Distance measurements appear in the 3D Manager results table and can be saved manually. The macro does not automatically export a CSV or save marked images.

## How to use

1. Install [Fiji](https://imagej.net/software/fiji/downloads) and the [3D ImageJ Suite](https://mcib3d.frama.io/3d-suite-imagej/#installation). Confirm that its 3D Manager is available in the Plugins menu.
2. Open the image stack and check its spatial calibration. Prepare the two marks/objects in a label image and add them to 3D Manager.
3. Select the two objects in 3D Manager and use its distance measurement function. Check the measurement type and units in the results before saving the table.
4. [Mark_points_measure_distance.ijm](Mark_points_measure_distance.ijm) is a short macro recording of part of this process. Open it by dragging it onto Fiji and inspect/adapt it before pressing **Run**.

## Current limitations

The recording creates a blank hyperstack with fixed dimensions and merges it with a window named `C2-mitosis.tif`. It assumes objects 0 and 1 are available for selection in 3D Manager. The manual point-drawing step is not recorded, and the example source image is not included. Treat the macro as a starting point for reproducing the manual workflow rather than a complete automated measurement tool.
