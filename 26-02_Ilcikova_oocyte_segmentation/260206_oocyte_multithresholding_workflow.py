"""
Oocyte Multi-Thresholding Workflow
===================================
Segments oocyte Z-stack images (2-channel .tif) into multiple ROIs using
multi-Otsu thresholding and measures channel-1 fluorescence intensity within
each ROI.  Produces per-image QC plots/overlays and an Excel summary.

Input:  Z-stacks in ZCYX order with 2 channels (ch1 = signal, ch2 = DAPI).
Output: mask_intensity_stats.xlsx  +  QC/ folder with bar-chart PNGs and
        composite overlay PNGs for every image.
"""

# =============================================================================
# 1. Imports
# =============================================================================
import os
import warnings

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import skimage
import skimage.io

warnings.filterwarnings("ignore", category=UserWarning)

# =============================================================================
# 2. Configuration – paths and output directories
# =============================================================================
# ADJUST PATHS!!!
data_dir = "D:/OneDrive - IEM/Z-stacks_Ilcikova"
output_dir = "D:/output_test"
QC_dirname = "QC"
table_filename = "mask_intensity_stats.xlsx"

min_oocyte_coverage = 0.25  # minimum area percentage that has to be covered by the oocyte mask; if below this, retry multi-Otsu with more classes
max_dapi_coverage = 0.25    # maximum area percentage that can be covered by the DAPI mask; if above this, switch to Yen thresholding

os.makedirs(output_dir, exist_ok=True)
os.makedirs(os.path.join(output_dir, QC_dirname), exist_ok=True)

output_path = os.path.join(output_dir, table_filename)

# =============================================================================
# 3. Discover image files (.tif, excluding "saturated" variants)
# =============================================================================
subdirs = [
    os.path.join(data_dir, d)
    for d in os.listdir(data_dir)
    if os.path.isdir(os.path.join(data_dir, d))
]

if subdirs:
    # Collect images from every subdirectory
    image_paths = []
    for subdir in sorted(subdirs):
        subdir_images = sorted([
            os.path.join(subdir, f)
            for f in os.listdir(subdir)
            if f.endswith(".tif") and "saturated" not in f
        ])
        image_paths.extend(subdir_images)
else:
    # Fall back to images directly in the root data directory
    image_paths = sorted([
        os.path.join(data_dir, f)
        for f in os.listdir(data_dir)
        if f.endswith(".tif") and "saturated" not in f
    ])

if not image_paths:
    raise FileNotFoundError(f"No image files found in {os.path.abspath(data_dir)}")

# =============================================================================
# 4. Helper functions
# =============================================================================

def mask_stats(image, mask):
    """Return (mean, std, pixel_count) for pixels of *image* inside *mask*."""
    masked_values = image[mask]
    if masked_values.size == 0:
        return np.nan, np.nan, 0
    return float(masked_values.mean()), float(masked_values.std()), int(masked_values.size)


def process_image(image_path):
    """Segment a single Z-stack into ROIs and measure channel-1 intensity.

    Processing steps
    ----------------
    1. Maximum-intensity projection (MIP) along Z.
    2. Median + Gaussian filtering of channel 1.
    3. Multi-Otsu thresholding to separate background / cytoplasm / nucleus.
    4. DAPI mask from channel 2 (Otsu, with Yen fallback if mask too large).
    5. Morphological cleanup and ring/circle masks for outer cytoplasm.
    6. Intensity statistics for every ROI measured on channel 1 MIP.

    Returns
    -------
    ch_1_mip, ch_2_mip : 2-D arrays  –  maximum-intensity projections.
    masks              : dict of bool arrays  –  named ROI masks.
    stats              : dict of (mean, std, area) tuples per ROI.
    All four are None when the image is skipped.
    """
    data = skimage.io.imread(image_path)
    print(f"Processing {os.path.basename(image_path)} | shape={data.shape}")

    # --- Validate channel count (expect ZCYX with C=2) ------------------
    if data.shape[1] != 2:
        print(f"  Skipping – expected 2 channels, got {data.shape[1]}")
        return None, None, None, None

    # --- Maximum-intensity projection along Z ----------------------------
    mip = np.max(data, axis=0).squeeze()       # shape: (C, Y, X)
    ch_1_mip = mip[0].squeeze()                # signal channel
    ch_2_mip = mip[1].squeeze()                # DAPI channel

    # =====================================================================
    # Channel 1: multi-Otsu segmentation into cytoplasm / nucleus
    # =====================================================================
    # Median filter to reduce salt-and-pepper noise, then heavy Gaussian
    # blur so that multi-Otsu operates on smooth intensity landscape.
    filtered_median = skimage.filters.rank.median(ch_1_mip, skimage.morphology.disk(3))
    blurred_gaussian = skimage.filters.gaussian(filtered_median, sigma=20, preserve_range=True)

    # Multi-Otsu with 3 classes (background / cytoplasm / nucleus).
    # If the oocyte mask covers < 25 % of the FOV the thresholds are too
    # aggressive – retry with 4 classes to better separate dim foreground.
    thresholds = skimage.filters.threshold_multiotsu(blurred_gaussian)
    binary_oocyte = blurred_gaussian >= thresholds[0]

    oocyte_coverage = np.sum(binary_oocyte) / binary_oocyte.size
    if oocyte_coverage < min_oocyte_coverage:
        print(f"Warning: Oocyte mask is very small ({oocyte_coverage * 100:.1f}%). Using 4 levels of thresholding instead.")
        thresholds = skimage.filters.threshold_multiotsu(blurred_gaussian, classes=4)

    # Middle and upper intensity bands from multi-Otsu
    binary_middle = (blurred_gaussian >= thresholds[0]) & (blurred_gaussian < thresholds[1])
    binary_upper = blurred_gaussian >= thresholds[1]

    # =====================================================================
    # Channel 2: DAPI mask and surroundings ring
    # =====================================================================
    filtered_median_ch2 = skimage.filters.rank.median(ch_2_mip, skimage.morphology.disk(3))

    # Otsu threshold; fall back to Yen if > 25 % coverage (over-segmented)
    thresh = skimage.filters.threshold_otsu(filtered_median_ch2)
    binary_ch2 = filtered_median_ch2 > thresh

    dapi_coverage = np.sum(binary_ch2) / binary_ch2.size
    if dapi_coverage > max_dapi_coverage:
        print(f"  Warning: DAPI mask is very large ({dapi_coverage * 100:.1f}%). Switching to Yen threshold")
        thresh = skimage.filters.threshold_yen(filtered_median_ch2)
        binary_ch2 = filtered_median_ch2 > thresh

    # Morphological open (erode then dilate) to remove small noise blobs
    eroded = skimage.morphology.binary_erosion(binary_ch2, skimage.morphology.disk(1))
    dapi_mask = skimage.morphology.binary_dilation(eroded, skimage.morphology.disk(1))

    # 20-pixel dilation ring around the DAPI mask
    dapi_surroundings = (
        skimage.morphology.binary_dilation(dapi_mask, skimage.morphology.disk(20))
        & ~dapi_mask
    )

    # =====================================================================
    # DAPI centroid and bounding circle (used to exclude DAPI neighbourhood
    # from the outer-cytoplasm ring)
    # =====================================================================
    coords = np.argwhere(dapi_mask)
    centroid = np.mean(coords, axis=0)
    distances = np.linalg.norm(coords - centroid, axis=1)
    radius = np.max(distances)

    circle_mask = np.zeros_like(binary_oocyte, dtype=bool)
    rr, cc = skimage.draw.disk(
        (centroid[0], centroid[1]), radius, shape=binary_oocyte.shape
    )
    circle_mask[rr, cc] = True

    # =====================================================================
    # Outer-cytoplasm ring: oocyte periphery minus DAPI neighbourhood
    # =====================================================================
    # Down-scale the oocyte mask for faster erosion, erode heavily to get
    # the inner core, then the ring = oocyte minus core.
    binary_oocyte = blurred_gaussian >= thresholds[0]
    binary_oocyte_ds = skimage.transform.resize(
        binary_oocyte,
        (binary_oocyte.shape[0] // 4, binary_oocyte.shape[1] // 4),
        order=0,
        preserve_range=True,
    ).astype(bool)

    padded_oocyte_ds = np.pad(binary_oocyte_ds, pad_width=1, mode='constant', constant_values=0)
    shrunk_mask = skimage.morphology.binary_erosion(
        padded_oocyte_ds, skimage.morphology.disk(50)
    )
    # Remove the 1-pixel padding
    shrunk_mask = shrunk_mask[1:-1, 1:-1]

    # Compute the peripheral ring and up-scale back to original resolution
    ring_mask = binary_oocyte_ds & ~shrunk_mask
    ring_mask = skimage.transform.resize(
        ring_mask, ch_1_mip.shape, order=0, preserve_range=True
    ).astype(bool)

    # Exclude the DAPI circle from the ring to get pure outer cytoplasm
    outer_cytoplasm = ring_mask & ~circle_mask

    # =====================================================================
    # Assemble named masks and compute intensity statistics on channel 1
    # =====================================================================
    cytoplasm_thresholded = binary_middle
    nucleus_thresholded = binary_upper
    nucleus_thresholded_without_DAPI = nucleus_thresholded & ~dapi_mask

    masks = {
        "DAPI_mask": dapi_mask,
        "DAPI_surroundings": dapi_surroundings,
        "outer_cytoplasm": outer_cytoplasm,
        "cytoplasm_thresholded": cytoplasm_thresholded,
        "nucleus_thresholded": nucleus_thresholded,
        "nucleus_thresholded_without_DAPI": nucleus_thresholded_without_DAPI,
    }

    stats = {name: mask_stats(ch_1_mip, mask) for name, mask in masks.items()}
    return ch_1_mip, ch_2_mip, masks, stats


def create_regions_overlay(ch_1_mip, ch_2_mip, masks, output_file):
    """Save a 512x512 RGB composite with channel merge and mask outlines.

    Red = channel 1, Blue = channel 2.  Mask boundaries are drawn in
    distinct colours for visual QC.
    """
    # Resize both channels to a fixed 512x512 thumbnail
    ch_1_resized = skimage.transform.resize(ch_1_mip, (512, 512), preserve_range=True)
    ch_2_resized = skimage.transform.resize(ch_2_mip, (512, 512), preserve_range=True)

    # Percentile-based contrast stretching (2nd–98th percentile)
    def auto_contrast(img):
        p2, p98 = np.percentile(img, (2, 98))
        return np.clip((img - p2) / (p98 - p2 + 1e-8) * 255, 0, 255).astype(np.uint8)

    ch_1_adj = auto_contrast(ch_1_resized)
    ch_2_adj = auto_contrast(ch_2_resized)

    # Compose RGB: ch1 -> red, ch2 -> blue
    rgb = np.zeros((512, 512, 3), dtype=np.uint8)
    rgb[:, :, 0] = ch_1_adj
    rgb[:, :, 2] = ch_2_adj

    # Overlay mask boundaries in distinct colours
    outline_colors = {
        "DAPI_mask":            (255, 255, 255),  # White
        "DAPI_surroundings":    (255, 255, 0),    # Yellow
        "outer_cytoplasm":      (0, 255, 255),    # Cyan
        "nucleus_thresholded":  (255, 0, 255),    # Magenta
    }

    for mask_name, color in outline_colors.items():
        if mask_name not in masks:
            continue
        mask_resized = skimage.transform.resize(
            masks[mask_name], (512, 512), order=0, preserve_range=True
        ).astype(bool)
        boundary = skimage.segmentation.find_boundaries(mask_resized, mode="outer")
        for c in range(3):
            rgb[:, :, c][boundary] = color[c]

    skimage.io.imsave(output_file, rgb)
    print(f"  Saved overlay -> {output_file}")


# =============================================================================
# 5. Main processing loop – segment every image and save QC outputs
# =============================================================================
all_rows = []

for image_path in image_paths:
    ch_1_mip, ch_2_mip, masks, stats = process_image(image_path)
    if ch_1_mip is None:
        continue  # skip images with unexpected channel count

    # --- Collect per-ROI statistics into a flat dict for the DataFrame ----
    row = {
        "image_name": os.path.basename(image_path),
        "parent_folder": os.path.basename(os.path.dirname(image_path)),
    }
    for name, (mean_val, std_val, count_val) in stats.items():
        row[f"{name}_mean"] = mean_val
        row[f"{name}_std"] = std_val
        row[f"{name}_area"] = count_val
    all_rows.append(row)

    # --- QC bar chart: mean +/- std per ROI for this image ----------------
    labels = list(stats.keys())
    means = [stats[n][0] for n in labels]
    stds = [stats[n][1] for n in labels]

    plt.figure(figsize=(10, 5))
    plt.bar(labels, means, yerr=stds, capsize=4)
    plt.ylabel("Mean intensity (ch 1 MIP)")
    plt.title(f"Mean +/- std per mask – {os.path.splitext(os.path.basename(image_path))[0]}")
    plt.xticks(rotation=30, ha="right")
    plt.tight_layout()

    stem = os.path.splitext(os.path.basename(image_path))[0]
    plot_file = os.path.join(output_dir, QC_dirname, f"stats_{stem}.png")
    plt.savefig(plot_file, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Saved plot   -> {plot_file}")

    # --- QC overlay: channel merge + mask outlines ------------------------
    overlay_file = os.path.join(output_dir, QC_dirname, f"regions_{stem}.png")
    create_regions_overlay(ch_1_mip, ch_2_mip, masks, overlay_file)

# =============================================================================
# 6. Export measurements to Excel and create folder-level summary plot
# =============================================================================
df = pd.DataFrame(all_rows)

# Derived metrics: difference and ratio of DAPI vs. outer-cytoplasm means
df.insert(2, "DAPI_minus_outer_cytoplasm_mean",
          df["DAPI_mask_mean"] - df["outer_cytoplasm_mean"])
df.insert(3, "DAPI_to_outer_cytoplasm_ratio",
          df["DAPI_mask_mean"] / df["outer_cytoplasm_mean"])

df.to_excel(output_path, index=False)
print(f"\nSaved measurements to {output_path}")

# --- Folder-level summary: mean +/- std of the difference metric ----------
folder_stats = (
    df.groupby("parent_folder")
    .agg({"DAPI_minus_outer_cytoplasm_mean": ["mean", "std"]})
    .reset_index()
)
folder_stats.columns = ["parent_folder", "mean", "std"]

plt.figure(figsize=(10, 5))
plt.bar(folder_stats["parent_folder"], folder_stats["mean"],
        yerr=folder_stats["std"].values, capsize=4)
plt.ylabel("Mean intensity difference")
plt.xlabel("Folder")
plt.title("DAPI minus outer cytoplasm by folder")
plt.xticks(rotation=30, ha="right")
plt.tight_layout()

summary_plot = os.path.join(output_dir, "DAPI_minus_outer_cytoplasm_by_folder.png")
plt.savefig(summary_plot, dpi=150, bbox_inches="tight")
plt.close()
print(f"Saved folder comparison plot to {summary_plot}")
