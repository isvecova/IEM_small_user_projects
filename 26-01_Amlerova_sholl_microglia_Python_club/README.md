# Glial-cell segmentation and Sholl analysis

## Goal

Explore segmentation, skeletonization and Sholl-style branching measurements of glial cells in microscopy images. This is an interactive Python Club workflow, with manual inspection of intermediate results.

## Input

An Andor `.ims` Z-stack. The main notebook expects a single timepoint with channels and Z-planes, uses channel index 0 for nuclei and index 1 for the glial signal, and performs analysis on 2D maximum-intensity projections.

## Output

Napari views of projections, segmented regions, skeletons and candidate cell centres; the full notebook also creates a branching-versus-radius plot with a mean and confidence band. Results remain in the notebook/Python session: there is no automatic table or image export. Save desired figures manually or add an export step.

## How to use

1. Install [Miniforge](https://conda-forge.org/download/) and create a Python environment:

   ```bash
   conda create -n amlerova-sholl python=3.11 -y
   conda activate amlerova-sholl
   python -m pip install jupyterlab bioio bioio-bioformats "napari[all]" numpy scikit-image matplotlib
   ```

   Reader setup is described in the [Bio-Formats plugin documentation](https://github.com/bioio-devs/bioio-bioformats#installation).

2. From this project folder, run `jupyter lab`. Start with [260121_Andor_3D_images_commented.ipynb](260121_Andor_3D_images_commented.ipynb) for the full analysis. The [commented_simple notebook](260121_Andor_3D_images_commented_simple.ipynb) demonstrates segmentation and visualization only.
3. Set `filepath` and check the channel order. Enable Qt interaction with `%gui qt` in a notebook code cell before creating napari viewers.
4. Run cells sequentially and inspect the segmentation and selected centres before interpreting the Sholl plot. Adjust filtering, thresholds and size limits to the images.

## Notes

Despite the 3D input, the current analysis is performed in 2D. Radii and filter sizes are in pixels; apply the acquisition's pixel calibration when interpreting distances. Merged skeletons or incorrect cell centres affect the measurements. Additional experiments are in `archive/`.
