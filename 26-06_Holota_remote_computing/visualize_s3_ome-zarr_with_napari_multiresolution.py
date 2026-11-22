"""
Open private S3 OME-Zarr MIP in napari using the full multiscale pyramid.

Install:
    pip install napari ome-zarr zarr s3fs fsspec dask numpy

Dataset:
    CYX multichannel MIP OME-Zarr
    NGFF 0.5-style metadata: root.attrs["ome"]["multiscales"]
"""

from __future__ import annotations

import configparser
from pathlib import Path
from typing import Any

import dask.array as da
import fsspec
import napari
import numpy as np
import zarr


# =============================================================================
# Configuration
# =============================================================================

OME_ZARR_S3_PATH = (
    "s3:///p02-26-holota-hydrogels/26PECMHZA_10_11_DAPI_CD68-488_CD86-594_CD206-647__20260609_114.ome.zarr"
)

S3_CREDENTIALS_FILE = Path.home() / ".s3_credentials"
S3_PROFILE = "P02_26-key1"

CHANNELS_TO_SHOW: list[int] | None = None

CHANNEL_COLORMAPS = [
    "blue",      # DAPI
    "green",     # CD68-488
    "magenta",   # CD86-594
    "cyan",      # CD206-647
]

CONTRAST_SAMPLE_STEP = 500
CONTRAST_PERCENTILES = (0.5, 99.8)


# =============================================================================
# S3 credentials
# =============================================================================

def make_s3_storage_options() -> dict[str, Any]:
    config = configparser.ConfigParser()
    read_files = config.read(S3_CREDENTIALS_FILE)

    if not read_files:
        raise FileNotFoundError(f"Could not read {S3_CREDENTIALS_FILE}")

    if S3_PROFILE not in config:
        raise ValueError(
            f"Profile '{S3_PROFILE}' not found in {S3_CREDENTIALS_FILE}"
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


# =============================================================================
# OME-Zarr helpers
# =============================================================================

def open_s3_mapper(path: str = OME_ZARR_S3_PATH):
    return fsspec.get_mapper(
        path,
        **make_s3_storage_options(),
    )


def join_s3_path(base: str, child: str) -> str:
    return base.rstrip("/") + "/" + child.lstrip("/")

def open_root_group(mapper) -> zarr.Group:
    return zarr.open_group(
        store=mapper,
        mode="r",
    )


def get_multiscales(root: zarr.Group):
    if "multiscales" in root.attrs:
        return root.attrs["multiscales"]

    if "ome" in root.attrs and "multiscales" in root.attrs["ome"]:
        return root.attrs["ome"]["multiscales"]

    raise ValueError(
        "No multiscales metadata found in root.attrs['multiscales'] "
        "or root.attrs['ome']['multiscales']."
    )


def get_multiscale_paths(root: zarr.Group) -> list[str]:
    multiscales = get_multiscales(root)
    datasets = multiscales[0]["datasets"]

    paths = [
        dataset["path"]
        for dataset in datasets
        if "path" in dataset
    ]

    if not paths:
        raise ValueError("No dataset paths found in multiscales metadata.")

    return paths


def read_multiscale_pyramid(root: zarr.Group) -> list[da.Array]:
    paths = get_multiscale_paths(root)

    pyramid = []

    for path in paths:
        level_s3_path = join_s3_path(OME_ZARR_S3_PATH, path)
        level_mapper = open_s3_mapper(level_s3_path)

        arr = da.from_zarr(level_mapper)
        pyramid.append(arr)

    return pyramid


def get_channel_names(root: zarr.Group, n_channels: int) -> list[str]:
    try:
        names = root.attrs["bioio"]["channel_names"]
        if names is not None and len(names) >= n_channels:
            return [str(names[i]) for i in range(n_channels)]
    except Exception:
        pass

    try:
        channels = root.attrs["omero"]["channels"]
        names = [
            ch.get("label", f"Channel {i}")
            for i, ch in enumerate(channels)
        ]
        if len(names) >= n_channels:
            return names[:n_channels]
    except Exception:
        pass

    fallback = [
        "DAPI",
        "CD68-488",
        "CD86-594",
        "CD206-647",
    ]

    if n_channels <= len(fallback):
        return fallback[:n_channels]

    return [f"Channel {i}" for i in range(n_channels)]


def get_scale_yx(root: zarr.Group) -> tuple[float, float]:
    try:
        multiscale = get_multiscales(root)[0]

        axes = multiscale["axes"]
        axis_names = [axis["name"] for axis in axes]

        transforms = multiscale["datasets"][0].get(
            "coordinateTransformations",
            [],
        )

        for transform in transforms:
            if transform.get("type") == "scale":
                scale = transform["scale"]
                y_scale = float(scale[axis_names.index("y")])
                x_scale = float(scale[axis_names.index("x")])
                return y_scale, x_scale

    except Exception:
        pass

    return 1.0, 1.0


def estimate_contrast_limits(
    channel_image_yx: da.Array,
    step: int = CONTRAST_SAMPLE_STEP,
    percentiles: tuple[float, float] = CONTRAST_PERCENTILES,
) -> tuple[float, float]:
    sample = channel_image_yx[::step, ::step].compute()

    low, high = np.percentile(sample, percentiles)

    if low == high:
        low = float(sample.min())
        high = float(sample.max())

    if low == high:
        high = low + 1.0

    return float(low), float(high)


# =============================================================================
# Main
# =============================================================================

def main() -> None:
    mapper = open_s3_mapper()
    root = open_root_group(mapper)

    pyramid = read_multiscale_pyramid(root)
    level0 = pyramid[0]

    if level0.ndim != 3:
        raise ValueError(
            f"Expected CYX image data, got level-0 shape {level0.shape}"
        )

    n_channels = level0.shape[0]
    channel_names = get_channel_names(root, n_channels)
    scale_yx = get_scale_yx(root)
    pyramid_paths = get_multiscale_paths(root)

    if CHANNELS_TO_SHOW is None:
        channels = list(range(n_channels))
    else:
        channels = CHANNELS_TO_SHOW

    print(f"Loaded: {OME_ZARR_S3_PATH}")
    print(f"Detected pyramid paths: {pyramid_paths}")
    print(f"Detected pyramid levels: {len(pyramid)}")
    print(f"Scale YX: {scale_yx}")

    for i, level in enumerate(pyramid):
        print(f"  level {i}: shape={level.shape}, chunks={level.chunks}")

    viewer = napari.Viewer()

    for ch in channels:
        if ch < 0 or ch >= n_channels:
            raise ValueError(
                f"Invalid channel index {ch}; image has {n_channels} channels."
            )

        channel_pyramid = [
            level[ch]
            for level in pyramid
        ]

        layer = viewer.add_image(
            channel_pyramid,
            name=channel_names[ch],
            multiscale=True,
            blending="additive",
            colormap=CHANNEL_COLORMAPS[ch % len(CHANNEL_COLORMAPS)],
            scale=scale_yx,
        )

        low, high = estimate_contrast_limits(level0[ch])
        layer.contrast_limits = (low, high)

        print(
            f"Channel {ch} ({channel_names[ch]}): "
            f"contrast=({low:.2f}, {high:.2f})"
        )

    napari.run()


if __name__ == "__main__":
    main()