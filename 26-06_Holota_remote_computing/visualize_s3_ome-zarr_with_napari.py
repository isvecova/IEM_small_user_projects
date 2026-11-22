"""
Open private S3 OME-Zarr MIP in napari.

Install:
    pip install napari ome-zarr zarr s3fs fsspec dask numpy
"""

from __future__ import annotations

import configparser
from pathlib import Path
from typing import Any

import dask.array as da
import fsspec
import napari
import zarr

OME_ZARR_S3_PATH = "s3:///p02-26-holota-hydrogels/26PECMHZA_10_11_DAPI_CD68-488_CD86-594_CD206-647__20260609_114.ome.zarr"

S3_CREDENTIALS_FILE = Path.home() / ".s3_credentials"
S3_PROFILE = "P02_26-key1"

# Usually full-resolution level written by ome-zarr-py
ZARR_ARRAY_COMPONENT = "s0"

# Show all channels, or specify e.g. [0, 1, 3]
CHANNELS_TO_SHOW: list[int] | None = None


def make_s3_storage_options() -> dict[str, Any]:
    config = configparser.ConfigParser()
    read_files = config.read(S3_CREDENTIALS_FILE)

    if not read_files:
        raise FileNotFoundError(f"Could not read {S3_CREDENTIALS_FILE}")

    if S3_PROFILE not in config:
        raise ValueError(f"Profile '{S3_PROFILE}' not found in {S3_CREDENTIALS_FILE}")

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


def open_root_group() -> zarr.Group:
    mapper = fsspec.get_mapper(
        OME_ZARR_S3_PATH,
        **make_s3_storage_options(),
    )
    return zarr.open_group(mapper, mode="r")


def get_channel_names(root: zarr.Group, n_channels: int) -> list[str]:
    try:
        names = root.attrs["bioio"]["channel_names"]
        if names is not None and len(names) >= n_channels:
            return [str(names[i]) for i in range(n_channels)]
    except Exception:
        pass

    return [f"Channel {i}" for i in range(n_channels)]


def get_scale_yx(root: zarr.Group) -> tuple[float, float]:
    try:
        multiscales = root.attrs["multiscales"]
        axes = multiscales[0]["axes"]
        axis_names = [axis["name"] for axis in axes]

        transforms = multiscales[0]["datasets"][0]["coordinateTransformations"]
        for transform in transforms:
            if transform.get("type") == "scale":
                scale = transform["scale"]
                y_scale = float(scale[axis_names.index("y")])
                x_scale = float(scale[axis_names.index("x")])
                return y_scale, x_scale
    except Exception:
        pass

    return 1.0, 1.0


def main() -> None:
    root = open_root_group()

    image_cyx = da.from_zarr(
        OME_ZARR_S3_PATH,
        component=ZARR_ARRAY_COMPONENT,
        storage_options=make_s3_storage_options(),
    )

    if image_cyx.ndim != 3:
        raise ValueError(f"Expected CYX data, got shape {image_cyx.shape}")

    n_channels, size_y, size_x = image_cyx.shape
    channel_names = get_channel_names(root, n_channels)
    scale_yx = get_scale_yx(root)

    print(f"Loaded: {OME_ZARR_S3_PATH}")
    print(f"Shape CYX: {image_cyx.shape}")
    print(f"Chunks: {image_cyx.chunks}")
    print(f"Scale YX: {scale_yx}")

    if CHANNELS_TO_SHOW is None:
        channels = list(range(n_channels))
    else:
        channels = CHANNELS_TO_SHOW

    viewer = napari.Viewer()

    for ch in channels:
        layer = viewer.add_image(
            image_cyx[ch],
            name=channel_names[ch],
            scale=scale_yx,
            blending="additive",
            colormap=["red", "green", "blue", "magenta", "cyan", "yellow"][ch % 6],
        )

        # Napari can autoscale lazily, but for sparse microscopy data,
        # setting contrast manually often helps.
        sample = image_cyx[ch][::500, ::500].compute()
        layer.contrast_limits = (
            float(sample.min()),
            float(sample.max()),
        )

    napari.run()


if __name__ == "__main__":
    main()