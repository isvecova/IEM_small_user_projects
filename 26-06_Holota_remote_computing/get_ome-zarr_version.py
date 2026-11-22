import ome_zarr
import zarr
import fsspec
import s3fs

print("ome_zarr:", ome_zarr.__version__)
print("zarr:", zarr.__version__)
print("fsspec:", fsspec.__version__)
print("s3fs:", s3fs.__version__)


import configparser
from pathlib import Path
from typing import Any

import fsspec
import zarr


OME_ZARR_S3_PATH = "s3:///p02-26-holota-hydrogels/26PECMHZA_10_11_DAPI_CD68-488_CD86-594_CD206-647__20260609_114.ome.zarr"

S3_CREDENTIALS_FILE = Path.home() / ".s3_credentials"
S3_PROFILE = "P02_26-key1"


def make_s3_storage_options() -> dict[str, Any]:
    config = configparser.ConfigParser()
    config.read(S3_CREDENTIALS_FILE)

    profile = config[S3_PROFILE]

    storage_options = {
        "anon": False,
        "key": profile["aws_access_key_id"],
        "secret": profile["aws_secret_access_key"],
    }

    if profile.get("endpoint_url"):
        storage_options["client_kwargs"] = {
            "endpoint_url": profile["endpoint_url"],
        }

    return storage_options


mapper = fsspec.get_mapper(
    OME_ZARR_S3_PATH,
    **make_s3_storage_options(),
)

root = zarr.open_group(mapper, mode="r")


def print_group(group, indent=0):
    prefix = "  " * indent

    print(f"{prefix}GROUP: {group.path!r}")
    print(f"{prefix}ATTR KEYS: {list(group.attrs.keys())}")

    for key in group.keys():
        obj = group[key]

        if isinstance(obj, zarr.Group):
            print_group(obj, indent + 1)
        else:
            print(f"{prefix}  ARRAY: {obj.path!r}, shape={obj.shape}, chunks={obj.chunks}")
            print(f"{prefix}  ARRAY ATTR KEYS: {list(obj.attrs.keys())}")


print_group(root)