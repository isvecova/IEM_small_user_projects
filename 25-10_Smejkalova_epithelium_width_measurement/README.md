# Exploring tissue border width from masks and skeletons

## Goal

Explore epithelial-region thickness using QuPath annotations, binary masks, distance transforms and profiles sampled along skeleton paths. The notebooks contain interactive development steps and require input/path preparation.

## Input and output

- [QuPath_test_Smejkalova/scripts/export_binary.groovy](QuPath_test_Smejkalova/scripts/export_binary.groovy) exports annotations of class **Epitel** to `QuPath_test_Smejkalova/export/<image>-labels.png`.
- [mask_analysis_Smejkalova.ipynb](mask_analysis_Smejkalova.ipynb) explores mask cleanup, distance transforms and skeleton profiles. Results are displayed in the notebook; a cell also saves a rendered `Dist.tif` image.
- [skeleton_analysis_Smejkalova.ipynb](skeleton_analysis_Smejkalova.ipynb) works from a skeleton TIFF and a matching distance-map TIFF, prunes skeleton paths and plots sampled values. The named skeleton/DT input files are not supplied in the current folder.

Profiles are for interpretation and further method development; no final measurement table is automatically exported.

## How to use

1. Install [QuPath](https://qupath.github.io/). Open the supplied project, relink source images if necessary and prepare **Epitel** annotations. Open the export script using **Automate > Show script editor**, with **Run > Include default imports** enabled, and run it on the current image.
2. Install [Miniforge](https://conda-forge.org/download/) and create a notebook environment:

   ```bash
   conda create -n smejkalova-width python=3.11 -y
   conda activate smejkalova-width
   python -m pip install jupyterlab numpy scipy scikit-image matplotlib networkx stackview tifffile
   ```

3. From this project folder, run `jupyter lab`. Set `mask_path` to the exported PNG and check `pixel_size` (currently 0.265 micrometres). Run the existing analysis code sequentially.
4. Both notebooks contain `bia_bob` initialization and `%bob` assistant prompts tied to an external service. For a manual analysis session, skip the assistant initialization and `%bob` lines while retaining the Python analysis code; the package list above covers that route.
5. Prepare matching skeleton and numerical distance-map TIFFs and update their paths before using the skeleton notebook.

## Notes

A distance transform measures distance to the nearest background pixel; it is not automatically a full border-width measurement. Check calibration and the geometric interpretation of the profile. The current `plt.imsave` export renders the distance map as an image: preserve/export the numerical `Dist` array separately for quantitative reuse. The notebooks are complementary experiments rather than a complete unattended pipeline.
