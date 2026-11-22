# Cellpose cell counting

## Goal

Segment cells in microscopy images with Cellpose and export a cell count for each image.

## Input

A folder containing image files readable by Cellpose, such as TIFF or PNG. The script uses the `cyto` model on the CPU, with automatic diameter estimation and `channels = [2, 1]` (green for segmentation, red as the nuclear channel in the Cellpose channel convention).

## Output

Files are saved beside the input images:

- `cellpose_roi_counts.csv`: image filename and number of segmented objects, without a header; open in a spreadsheet for further analysis.
- `*_seg.npy`: segmentation data for inspection in Cellpose.
- PNG masks and segmentation previews for visual checking. This export is intended for 2D images.

## How to use

1. Install [Miniforge](https://conda-forge.org/download/) and open Miniforge Prompt. The script uses the older Cellpose 2 API; [Cellpose 2.2.3](https://github.com/MouseLand/cellpose/tree/v2.2.3) has the helper functions and argument order used here. An example setup is:

   ```bash
   conda create -n filova-cellpose python=3.10 -y
   conda activate filova-cellpose
   python -m pip install "cellpose==2.2.3" "numpy<2" "torch<2.6" matplotlib
   ```

2. Open [Cellpose_cell_counting_batch.py](Cellpose_cell_counting_batch.py), change the path in `os.chdir(...)`, and check the model and channel settings for your images.
3. Use a folder containing only the input images: the script currently reads every directory entry, including outputs left from previous runs.
4. From this project folder, run:

   ```bash
   python Cellpose_cell_counting_batch.py
   ```

5. Inspect the masks before using the counts.

## Notes

The setup above targets the legacy API; it is not a recovered or tested environment from the original analysis. The script converts input intensities directly to `uint8`, so higher-bit-depth data require checking before reuse. All images are loaded into memory together.
