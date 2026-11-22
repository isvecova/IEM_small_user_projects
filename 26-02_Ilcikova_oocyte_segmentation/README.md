# Oocyte segmentation workflow

## Goal of the analysis

**Automatically segment images of oocytes into nucleus and cytoplasm and measure signal of channel 1 (DNA repair proteins), corrected for unspecific signal in the cytoplasm.**

In the oocyte images used for testing, DAPI was not covering a circular area, but was condensed. Fore some proteins, the rest of the circular nucleus was still visible, for some not. 

Several areas were segmented and measured to account for that:
- **DAPI_mask** - area with positive DAPI signal
- **outer_cytoplasm** - outer part of the cytoplasm obtained by binary erosion - should be the most representative area with unspecific cytoplasm signal
- DAPI_surrroundings - area of a few pixels (value specified in the script) around the DAPI_mask
- cytoplasm_thresholded - area segmented from channel 1 between first and second threshold value from multi-Otsu threholding (sometimes, it might also take up parts of the nucleus, if it is not clearly defined)
- nucleus_thresholded - area of channel 1 signal above the second threshold value from multi-Otsu thresholding (sometimes not clearly defined)
- nucleus_thresholded_without_DAPI - nucleus_thresholded minus the DAPI positive area - for getting an idea about signal distribution in circular nuclear area outside of the condensed DAPI

The first two areas (DAPI_mask and outer_cytoplasm) are the most reliably segmented (segmented correctly in most images) and therefore are used for final measurement of subtraction and ratio. 


## What this script does

The script `260206_oocyte_multithresholding_workflow.py` processes 2-channel Z-stack TIF images and measures signal intensity in biologically meaningful regions.

Expected image layout:
- Format: **.tif**
- Shape order: **Z, C, Y, X**
- Number of channels: **2**
  - Channel 1 = signal (quantified)
  - Channel 2 = DAPI (used for DAPI mask)
- Image obtained pixel size of 0.0523066 micrometer, covering the whole oocyte and a bit of surrounding space. **For different pixel size, parameters might have to be adjusted accordingly**.

For each image, the script:
1. Loads the Z-stack and checks channel count.
2. Creates max-intensity projections (MIP) for both channels.
3. Segments channel 1 with median + Gaussian filtering and multi-Otsu thresholds (3 classes by default, fallback to 4 classes if the cytoplasm is not segmented properly and covers less than 25% of the image).
4. Segments DAPI on channel 2 with Otsu thresholding (fallback to Yen if threshold is too low - DAPI mask covers more than 25% of the image).
5. Builds derived masks (DAPI surroundings, outer cytoplasm ring, threshold-based cytoplasm/nucleus masks).
6. Measures channel-1 intensity statistics inside each mask:
   - mean
   - standard deviation
   - area (pixel count)
7. Saves QC outputs:
   - per-image bar plot of ROI mean ± std
   - per-image overlay (merged channels + mask outlines)
8. Exports all image-level measurements to Excel.
9. Computes and plots folder-level summary for `DAPI_minus_outer_cytoplasm_mean`.

---

## Output files

In `output_dir` (configured in the script):

- `mask_intensity_stats.xlsx`
  - one row per image
  - includes per-mask mean/std/area
  - includes derived metrics:
    - `DAPI_minus_outer_cytoplasm_mean` = mean channel 1 intensity in DAPI positive area **minus** mean intensity in outer cytoplasm
    - `DAPI_to_outer_cytoplasm_ratio` = **ratio** of mean channel 1 intensity in DAPI positive area to mean intensity in outer cytoplasm

- `QC/` folder
  - `stats_<image_stem>.png` (bar plot)
  - `regions_<image_stem>.png` (overlay with mask outlines)

- `DAPI_minus_outer_cytoplasm_by_folder.png`
  - folder-level mean ± std chart

---

## How to use

### Requirements
- Functional Python installation, ideally as conda environment (described in the Python installation file).
- Folder containing images in `.tif` format - can be either in the main folder or in subfolders within the main folder. If there are subfolders, each subfolder's name will be added to the table to the `parent_folder` column.

### 1) Set paths in the script
In the **Configuration** section, update:
- `data_dir` = folder containing your `.tif` files (or subfolders with `.tif` files)
- `output_dir` = destination for Excel and QC outputs

Notes:
- Files with `"saturated"` in the filename are automatically excluded.
- If subfolders exist in `data_dir`, images are collected from subfolders; otherwise from `data_dir` root.

### 2) If not yet created, create a conda environment and install dependencies

Conda environment installation is described in more detail in another document (Python_installation.md). 

Dependencies needed: 
```bash
pip install numpy pandas matplotlib scikit-image openpyxl
```

(`openpyxl` is needed for writing `.xlsx`.)

### 3) Run
1. Open Miniforge (or Miniconda) Prompt. 
2. Activate the corresponding environment with the dependencies installed.
3. Run the script with the following command:

```bash
python 260206_oocyte_multithresholding_workflow.py
```

### 4) Review outputs
- Open `mask_intensity_stats.xlsx` for quantitative results.
- Inspect `QC` images to verify segmentation quality.
- Check the folder summary plot for between-folder differences.

---

## Practical reuse tips

- If the script does not work, make sure the paths are set properly.
- If your image dimensions or channel order differ from `ZCYX`, make sure it has not been turned into an RGB image.
- If segmentation is too small/large for your data, tune:
  - Gaussian sigma (`sigma=20`)
  - Maximum DAPI coverage (`0.25`)
  - Minimum oocyte coverage (`0.25`)
  - ring construction erosion/dilation settings

---
Written for: Terka Ilčíková

Written in February 2026 by Iva Švecová
