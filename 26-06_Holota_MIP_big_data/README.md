# Maximum-intensity projections of large VSI images

**This is an experimental project that was not handed-over to the user.**

## Goal

Create a Z maximum-intensity projection (MIP) for each multichannel Olympus/Evident `.vsi` stack in a folder, using lazy image reading with Dask.

## Input

VSI Z-stacks with their associated data files/folders intact. The script processes the selected BioIO scene (`resolution_level`, currently 0) and the first timepoint. Images with only one Z-plane are skipped.

## Output

One `MIP_<index>_<original_name>.ome.tif` per processed stack in `save_dir`, preserving the channels in CYX order. Open the projections in Fiji or napari for inspection and downstream 2D analysis. Processing times and failures are printed to the terminal.

Although the filename ends in `.ome.tif`, the active writer creates an **ImageJ-format TIFF**, with axis metadata but no explicit physical pixel-size metadata. Reapply the acquisition calibration when needed; the OME writer call is commented out.

## How to use

1. Install [Miniforge](https://conda-forge.org/download/) and open Miniforge Prompt:

   ```bash
   conda create -n holota-mip python=3.11 -y
   conda activate holota-mip
   python -m pip install bioio bioio-bioformats bioio-ome-tiff "dask[array]" numpy tifffile
   ```

   See the [Bio-Formats reader installation notes](https://github.com/bioio-devs/bioio-bioformats#installation) for runtime setup. `bioio-ome-tiff` supplies the writer imported by the script, even though that writer's save call is disabled.

2. Keep [logback.xml](logback.xml) beside [do_mip_dask.py](do_mip_dask.py). Edit `input_dir`, `save_dir` and `resolution_level` in the script.
3. From this project folder, run:

   ```bash
   python do_mip_dask.py
   ```

4. Inspect a projection and check the terminal for `FAILED` messages before processing a larger dataset.

## Notes

Reading is lazy, but `mip.compute()` loads the complete final projection into RAM. Rerunning the same input/output configuration replaces matching output files. `T_metadata_extraction.ipynb` is an auxiliary metadata-inspection notebook.
