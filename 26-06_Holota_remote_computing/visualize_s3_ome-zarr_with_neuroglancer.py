"""
View S3-hosted OME-Zarr MIP data in Neuroglancer.

This expects the OME-Zarr written by the previous script:
    axes: C, Y, X
    pyramid level 0 stored at component "0"

Install:
    pip install neuroglancer dask zarr s3fs fsspec numpy

Recommended:
    pip install "zarr<3"

Run:
    python view_s3_omezarr_neuroglancer.py

Then open the printed Neuroglancer URL in your browser.
"""

from __future__ import annotations

import configparser
from pathlib import Path
from typing import Any

import dask.array as da
import fsspec
import neuroglancer
import numpy as np
import zarr


# =============================================================================
# Configuration
# =============================================================================

OME_ZARR_S3_PATH = "s3:///p02-26-holota-hydrogels/26PECMHZA_10_11_DAPI_CD68-488_CD86-594_CD206-647__20260609_114.ome.zarr"

# Full-resolution pyramid level.
# For ome-zarr-py output this is usually "0".
ZARR_ARRAY_COMPONENT = "s0"

# Credentials file outside your project folder
S3_CREDENTIALS_FILE = Path.home() / ".s3_credentials"
S3_PROFILE = "P02_26-key1"

# Neuroglancer server
BIND_ADDRESS = "127.0.0.1"
PORT = 9999

# Optional display settings
AUTO_CONTRAST_PERCENTILES = (0.5, 99.5)

# If you have many channels, you can restrict them here.
# None -> show all channels
CHANNELS_TO_SHOW: list[int] | None = None

# Names used if metadata channel names are missing
DEFAULT_CHANNEL_NAMES = {
    0: "Channel 0",
    1: "Channel 1",
    2: "Channel 2",
    3: "Channel 3",
}

# Simple default shader colours
CHANNEL_COLORS = {
    0: "red",
    1: "green",
    2: "blue",
    3: "magenta",
    4: "cyan",
    5: "yellow",
}


# =============================================================================
# S3 helpers
# =============================================================================

def make_s3_storage_options() -> dict[str, Any]:
    config = configparser.ConfigParser()
    read_files = config.read(S3_CREDENTIALS_FILE)

    if not read_files:
        raise FileNotFoundError(
            f"Could not read credentials file: {S3_CREDENTIALS_FILE}"
        )

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


def open_zarr_group() -> zarr.Group:
    mapper = fsspec.get_mapper(
        OME_ZARR_S3_PATH,
        **make_s3_storage_options(),
    )

    return zarr.open_group(
        mapper,
        mode="r",
    )


def open_dask_array() -> da.Array:
    storage_options = make_s3_storage_options()

    arr = da.from_zarr(
        OME_ZARR_S3_PATH,
        component=ZARR_ARRAY_COMPONENT,
        storage_options=storage_options,
    )

    return arr


# =============================================================================
# Metadata helpers
# =============================================================================

def get_channel_names(root: zarr.Group, n_channels: int) -> list[str]:
    """
    Try to read channel names stored by the converter script.
    Falls back to generic names.
    """
    try:
        names = root.attrs["bioio"]["channel_names"]
        if names is not None and len(names) >= n_channels:
            return [str(names[i]) for i in range(n_channels)]
    except Exception:
        pass

    return [
        DEFAULT_CHANNEL_NAMES.get(i, f"Channel {i}")
        for i in range(n_channels)
    ]


def get_xy_scale_um(root: zarr.Group) -> tuple[float, float]:
    """
    Try to extract pixel size from OME-Zarr multiscale metadata.

    Returns:
        y_scale_um, x_scale_um
    """
    try:
        multiscales = root.attrs["multiscales"]
        datasets = multiscales[0]["datasets"]
        coordinate_transformations = datasets[0]["coordinateTransformations"]

        for transform in coordinate_transformations:
            if transform.get("type") == "scale":
                scale = transform["scale"]

                axes = multiscales[0]["axes"]
                axis_names = [ax["name"] for ax in axes]

                y_scale = float(scale[axis_names.index("y")])
                x_scale = float(scale[axis_names.index("x")])

                return y_scale, x_scale

    except Exception:
        pass

    return 1.0, 1.0


def compute_contrast_limits(
    image_cyx: da.Array,
    channel: int,
    percentiles: tuple[float, float],
) -> tuple[float, float]:
    """
    Estimate display limits from a downsampled view of one channel.

    This avoids reading the whole image.
    """
    img = image_cyx[channel]

    step_y = max(1, img.shape[0] // 2048)
    step_x = max(1, img.shape[1] // 2048)

    sample = img[::step_y, ::step_x].compute()
    low, high = np.percentile(sample, percentiles)

    print(low, high)

    if low == high:
        low = float(sample.min())
        high = float(sample.max())

    if low == high:
        high = low + 1

    return float(low), float(high)


# =============================================================================
# Neuroglancer helpers
# =============================================================================

class LazyDaskVolume:
    """
    Minimal NumPy-like wrapper for Neuroglancer LocalVolume.

    Neuroglancer requests small chunks/slices.
    This wrapper computes only the requested Dask slice.
    """

    def __init__(self, array: da.Array):
        self.array = array
        self.shape = array.shape
        self.dtype = array.dtype
        self.ndim = array.ndim

    def __getitem__(self, item):
        return np.asarray(self.array[item].compute())


def make_shader(
    color: str,
    low: float,
    high: float,
) -> str:
    return f"""
void main() {{
  float v = toNormalized(getDataValue(), {low:.6g}, {high:.6g});
  emitRGB(vec3(v) * vec3({color_to_rgb(color)}));
}}
"""


def color_to_rgb(color: str) -> str:
    colours = {
        "red": "1.0, 0.0, 0.0",
        "green": "0.0, 1.0, 0.0",
        "blue": "0.0, 0.0, 1.0",
        "magenta": "1.0, 0.0, 1.0",
        "cyan": "0.0, 1.0, 1.0",
        "yellow": "1.0, 1.0, 0.0",
        "gray": "1.0, 1.0, 1.0",
        "grey": "1.0, 1.0, 1.0",
    }

    return colours.get(color, "1.0, 1.0, 1.0")


def launch_neuroglancer() -> None:
    root = open_zarr_group()
    image_cyx = open_dask_array()

    if image_cyx.ndim != 3:
        raise ValueError(
            f"Expected CYX array, got shape {image_cyx.shape}"
        )

    n_channels, size_y, size_x = image_cyx.shape

    y_scale_um, x_scale_um = get_xy_scale_um(root)

    channel_names = get_channel_names(root, n_channels)

    if CHANNELS_TO_SHOW is None:
        channels = list(range(n_channels))
    else:
        channels = CHANNELS_TO_SHOW

    print(f"Opened: {OME_ZARR_S3_PATH}")
    print(f"Array shape CYX: {image_cyx.shape}")
    print(f"Array chunks: {image_cyx.chunks}")
    print(f"Pixel size: y={y_scale_um} µm, x={x_scale_um} µm")
    print(f"Channels shown: {channels}")

    # neuroglancer.set_server_bind_address(
    #     bind_address=BIND_ADDRESS,
    #     bind_port=PORT,
    # )

    neuroglancer.set_server_bind_address("127.0.0.1", 9999)

    viewer = neuroglancer.Viewer()

    dimensions = neuroglancer.CoordinateSpace(
        names=["z", "y", "x"],
        units=["um", "um", "um"],
        scales=[1.0, y_scale_um, x_scale_um],
    )

    with viewer.txn() as state:
        state.layout = "xy"

        for ch in channels:
            if ch < 0 or ch >= n_channels:
                raise ValueError(
                    f"Invalid channel index {ch}; image has {n_channels} channels."
                )

            # Convert CYX channel to ZYX with singleton Z.
            channel_zyx = image_cyx[ch][None, :, :]

            low, high = compute_contrast_limits(
                image_cyx=image_cyx,
                channel=ch,
                percentiles=AUTO_CONTRAST_PERCENTILES,
            )

            colour = CHANNEL_COLORS.get(ch, "gray")
            layer_name = channel_names[ch]

            # state.layers[layer_name] = neuroglancer.ImageLayer(
            #     source=neuroglancer.LocalVolume(
            #         data=LazyDaskVolume(channel_zyx),
            #         dimensions=dimensions,
            #         voxel_offset=[0, 0, 0],
            #     ),
            #     shader=make_shader(
            #         color=colour,
            #         low=low,
            #         high=high,
            #     ),
            # )

            state.layers[layer_name] = neuroglancer.ImageLayer(
                source=neuroglancer.LocalVolume(
                    data=LazyDaskVolume(channel_zyx),
                    dimensions=dimensions,
                    voxel_offset=[0, 0, 0],
                ),
            )


    print("\nOpen this URL in your browser:")
    # print(viewer)
    print(viewer.get_viewer_url())

    input("\nPress Enter to stop the Neuroglancer server...")


if __name__ == "__main__":
    launch_neuroglancer()