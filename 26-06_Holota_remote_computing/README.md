# Remote storage and viewing of microscopy projections

**This is an experimental project that was not handed-over to the user.**

## Goal

Convert a multichannel VSI Z-stack to a maximum-intensity projection stored as multiscale OME-Zarr on S3, then view it without downloading the entire dataset first.

## Input and output

Input is a `.vsi` stack with its associated data files, S3 storage access and a credentials profile. The writer produces a channel-preserving CYX projection with resolution levels and selected source metadata in an S3 `.ome.zarr` store. The viewers display that store in napari or a browser via Neuroglancer. Keep the original VSI data: the projection discards the Z dimension.

## How to use

1. Install Python through [Miniforge](https://conda-forge.org/download/) and create a separate project environment. Dependencies listed by the scripts are `bioio`, `bioio-bioformats`, `ome-zarr`, `zarr`, `s3fs`, `fsspec`, `dask`, `distributed` and `numpy`; add `napari[all]` for the napari viewer or `neuroglancer` for browser viewing. See the [Bio-Formats reader setup](https://github.com/bioio-devs/bioio-bioformats#installation).
2. Use compatible OME-Zarr/Zarr versions: the writer imports `FormatV05` and targets NGFF 0.5, while the Neuroglancer script suggests `zarr<3`. There is no environment lockfile, so a single verified install command for all scripts is not available. Reuse a working environment or confirm compatibility on a small example first.
3. Create the credentials file expected by the scripts, `~/.s3_credentials` (on Windows, in your user home folder), using your own account details:

   ```ini
   [P02_26-key1]
   aws_access_key_id = YOUR_ACCESS_KEY
   aws_secret_access_key = YOUR_SECRET_KEY
   endpoint_url = https://YOUR_S3_ENDPOINT
   ```

4. In [store_mip_ome-zarr_s3.py](store_mip_ome-zarr_s3.py), set `INPUT_FILE`, `SCENE`, `S3_OUTPUT`, `S3_PROFILE` and `OVERWRITE`. From this project folder and with the environment activated, run `python store_mip_ome-zarr_s3.py`.
5. Set `OME_ZARR_S3_PATH` and the credentials profile in [visualize_s3_ome-zarr_with_napari_multiresolution.py](visualize_s3_ome-zarr_with_napari_multiresolution.py), then run `python visualize_s3_ome-zarr_with_napari_multiresolution.py`. This viewer reads pyramid paths from the metadata.

## Notes

`OVERWRITE` defaults to `True`. The other napari viewer and [Neuroglancer viewer](visualize_s3_ome-zarr_with_neuroglancer.py) use a configured `ZARR_ARRAY_COMPONENT` (currently `s0`), which must match the actual store. Neuroglancer prints a browser URL; leave its Python process running while viewing. [get_ome-zarr_version.py](get_ome-zarr_version.py) helps inspect versions/store contents. The `.ipynb` file is exploratory teaching material.
