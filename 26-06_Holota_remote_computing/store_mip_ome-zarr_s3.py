"""
Convert a large .vsi image to a Z-MIP OME-Zarr stored directly on S3.

Input:
    .vsi file, typically Olympus / Evident cellSens

Output:
    OME-Zarr containing a channel-preserving Z maximum-intensity projection.

Install:
    pip install bioio bioio-bioformats ome-zarr zarr s3fs dask distributed numpy

Notes:
    - Java must be available for bioio-bioformats.
    - Keep the original .vsi/.ets data as the archival raw data.
    - This script stores selected BioIO/Bio-Formats metadata as Zarr attributes,
      but not all proprietary VSI metadata can be cleanly mapped to OME-Zarr.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import dask.array as da
import fsspec
import zarr
from bioio import BioImage
from ome_zarr.format import FormatV05
from ome_zarr.scale import Methods
from ome_zarr.writer import write_image
import configparser


# =============================================================================
# Configuration
# =============================================================================

INPUT_FILE = Path(
    r"N:\01_scientific_data\260630_holota_hydrogel_spinal_cord\26PECMHZA_10_11_DAPI_CD68%488_CD86%594_CD206%647__20260609_114.vsi"
)

# None -> BioIO default scene
# int  -> scene index, e.g. 0
# str  -> exact scene name
SCENE: int | str | None = None

S3_OUTPUT = "s3:///p02-26-holota-hydrogels/26PECMHZA_10_11_DAPI_CD68-488_CD86-594_CD206-647__20260609_114.ome.zarr"

S3_CREDENTIALS_FILE = Path.home() / ".s3_credentials"
S3_PROFILE = "P02_26-key1"

OVERWRITE = True

# Output array is C, Y, X
CHUNKS_CYX = (1, 1024, 1024)

# Pyramid downsampling factors for Y/X
PYRAMID_LEVELS = (2, 4, 8, 16)
PYRAMID_METHOD = Methods.LOCAL_MEAN

STORE_EXTRA_METADATA = True
STORE_OME_XML_IF_AVAILABLE = True


# =============================================================================
# Helper functions
# =============================================================================

def json_safe(value: Any) -> Any:
    try:
        json.dumps(value)
        return value
    except Exception:
        return repr(value)


def select_scene(img: BioImage, scene: int | str | None) -> None:
    if scene is None:
        return

    if isinstance(scene, int):
        img.set_scene(img.scenes[scene])
    else:
        img.set_scene(scene)


def get_scale_um_for_mip(img: BioImage) -> dict[str, float]:
    pps = getattr(img, "physical_pixel_sizes", None)

    scale: dict[str, float] = {}

    if pps is not None and getattr(pps, "Y", None) is not None:
        scale["y"] = float(pps.Y)

    if pps is not None and getattr(pps, "X", None) is not None:
        scale["x"] = float(pps.X)

    return scale


def get_channel_names(img: BioImage) -> list[str] | None:
    md = getattr(img, "metadata", None)
    if md is None:
        return None
    
    try:
        image_meta = md.images[0]
        channels = image_meta.pixels.channels
        return [
            ch.name if ch.name is not None else f"Channel {i}"
            for i, ch in enumerate(channels)
        ]
    except (AttributeError, IndexError):
        return None


def extract_extra_metadata(img: BioImage, source_path: Path) -> dict[str, Any]:
    attrs: dict[str, Any] = {
        "source_file": str(source_path),
        "source_format": "Olympus/Evident cellSens VSI",
        "conversion": {
            "operation": "Z maximum-intensity projection",
            "input_dimension_order": "CZYX",
            "output_dimension_order": "CYX",
        },
        "bioio": {
            "scenes": json_safe(list(getattr(img, "scenes", []))),
            "current_scene": json_safe(getattr(img, "current_scene", None)),
            "dims": json_safe(str(getattr(img, "dims", ""))),
            "shape": json_safe(getattr(img, "shape", None)),
            "physical_pixel_sizes": json_safe(
                getattr(img, "physical_pixel_sizes", None)
            ),
            "channel_names": json_safe(get_channel_names(img)),
        },
    }

    md = getattr(img, "metadata", None)

    if md is not None:
        attrs["bioio"]["metadata_repr"] = json_safe(md)

        if STORE_OME_XML_IF_AVAILABLE and hasattr(md, "to_xml"):
            try:
                attrs["bioio"]["ome_xml"] = md.to_xml()
            except Exception as exc:
                attrs["bioio"]["ome_xml_error"] = repr(exc)

    return attrs


def make_s3_storage_options() -> dict[str, Any]:
    config = configparser.ConfigParser()
    config.read(S3_CREDENTIALS_FILE)

    if S3_PROFILE not in config:
        raise ValueError(
            f"S3 profile '{S3_PROFILE}' not found in {S3_CREDENTIALS_FILE}"
        )

    profile = config[S3_PROFILE]

    storage_options: dict[str, Any] = {
        "anon": False,
        "key": profile["aws_access_key_id"],
        "secret": profile["aws_secret_access_key"],
    }

    if profile.get("aws_session_token"):
        storage_options["token"] = profile["aws_session_token"]

    if profile.get("endpoint_url"):
        storage_options["client_kwargs"] = {
            "endpoint_url": profile["endpoint_url"],
        }

    return storage_options


def open_output_group(s3_url: str) -> zarr.Group:
    mapper = fsspec.get_mapper(
        s3_url,
        **make_s3_storage_options(),
    )

    return zarr.group(
        store=mapper,
        overwrite=OVERWRITE,
    )


# =============================================================================
# Main conversion
# =============================================================================

def convert_vsi_mip_to_s3_omezarr() -> None:
    print(f"Opening: {INPUT_FILE}")

    img = BioImage(INPUT_FILE)
    select_scene(img, SCENE)

    print("Available scenes:")
    for i, scene_name in enumerate(img.scenes):
        marker = "  <-- selected" if scene_name == img.current_scene else ""
        print(f"  [{i}] {scene_name}{marker}")

    print(f"Selected scene: {img.current_scene}")
    print(f"Image dimensions: {img.dims}")
    print(f"Image shape: {img.shape}")
    print(f"Physical pixel sizes: {img.physical_pixel_sizes}")

    # Read lazily as CZYX.
    # This assumes there is no real time axis in the file.
    data_czyx = img.get_image_dask_data("CZYX")

    print(
        f"Loaded lazy data as CZYX: "
        f"shape={data_czyx.shape}, dtype={data_czyx.dtype}"
    )

    # Z maximum-intensity projection:
    # CZYX -> CYX
    mip_cyx = da.max(data_czyx, axis=1)

    mip_cyx = mip_cyx.rechunk(CHUNKS_CYX)

    print(f"MIP shape CYX: {mip_cyx.shape}")
    print(f"MIP chunks CYX: {mip_cyx.chunks}")
    print(f"Writing to: {S3_OUTPUT}")

    root = open_output_group(S3_OUTPUT)

    scale = get_scale_um_for_mip(img)

    axes_units = None
    if scale:
        axes_units = {
            "y": "micrometer",
            "x": "micrometer",
        }

    write_image(
        image=mip_cyx,
        group=root,
        axes=["c", "y", "x"],
        scale=scale or None,
        axes_units=axes_units,
        scale_factors=list(PYRAMID_LEVELS),
        method=PYRAMID_METHOD,
        fmt=FormatV05(),
        storage_options={
            "chunks": CHUNKS_CYX,
        },
        compute=True,
        name=INPUT_FILE.stem,
    )

    if STORE_EXTRA_METADATA:
        root.attrs.update(
            extract_extra_metadata(
                img=img,
                source_path=INPUT_FILE,
            )
        )

    print("Finished.")


if __name__ == "__main__":
    convert_vsi_mip_to_s3_omezarr()