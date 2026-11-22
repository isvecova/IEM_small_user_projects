from pathlib import Path
import os
import time
from time import perf_counter
from collections import defaultdict

import os
from pathlib import Path

logback_path = Path(__file__).with_name("logback.xml").resolve()
os.environ["JAVA_TOOL_OPTIONS"] = (
    f'-Dlogback.configurationFile="{logback_path}"'
)

import dask.array as da
import tifffile
from bioio import BioImage

import numpy as np
from bioio.writers import OmeTiffWriter # with bioio-ome-tiff installed

resolution_level = 0

input_dir = Path(r"L:\Olympus_SpinSR10\530\rado")
save_dir = Path(r"N:\01_scientific_data\Holota_MIP_big_data\MIP_OME_TIFF")
save_dir.mkdir(parents=True, exist_ok=True)

print("Starting, looks good")

# Overall script start
script_start = perf_counter()

group_counters = defaultdict(int)


for file_path in sorted(input_dir.glob("*.vsi")):
    print(f"Processing: {file_path}")

    group_name = file_path.stem

    group_counters[group_name] += 1
    group_index = group_counters[group_name]

    # Per-file timing
    file_start = perf_counter()
    try:
        step_start = perf_counter()
        img = BioImage(file_path)
        print(f"  Opened image (elapsed {perf_counter()-step_start:.3f}s)")

        step_start = perf_counter()
        # Equivalent to Bio-Formats series_list=resolutionLevel
        img.set_scene(resolution_level)
        print(f"  set_scene (elapsed {perf_counter()-step_start:.3f}s)")

        step_start = perf_counter()
        # Read lazily as CZYX for first timepoint
        data = img.get_image_dask_data("CZYX", T=0)
        print(f"  get_image_dask_data (elapsed {perf_counter()-step_start:.3f}s)")

        # data shape: C, Z, Y, X
        n_channels, n_z, _, _ = data.shape

        if n_z <= 1:
            print("  not a z-stack")
            continue

        step_start = perf_counter()
        # Max intensity projection over Z
        mip = da.max(data, axis=1)  # result: C, Y, X
        print(f"  projection (da.max) created (elapsed {perf_counter()-step_start:.3f}s)")

        step_start = perf_counter()
        # Compute only final projected image
        mip_np = mip.compute()
        print(f"  compute() finished (elapsed {perf_counter()-step_start:.3f}s)")

        step_start = perf_counter()
        original_name = file_path.stem
        save_path = save_dir / f"MIP_{group_index}_{original_name}.ome.tif"

        # Save as ImageJ-compatible TIFF, channels preserved
        # OmeTiffWriter.save(mip_np, save_path, dim_order="CYX")
        tifffile.imwrite(
            save_path,
            mip_np,
            imagej=True,
            metadata={"axes": "CYX"},
        )
        print(f"  write finished (elapsed {perf_counter()-step_start:.3f}s)")

        total_file_elapsed = perf_counter() - file_start
        print(f"MIP done; Saved: {save_path} (total {total_file_elapsed:.3f}s)")

    except Exception as e:
        total_file_elapsed = perf_counter() - file_start
        print(f"FAILED: {file_path} (after {total_file_elapsed:.3f}s)")
        print(e)

total_elapsed = perf_counter() - script_start
print(f"FINISHED; all done (total script time: {total_elapsed:.3f}s)")