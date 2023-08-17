import os
import yaml
import json
import argparse
import sys
from pathlib import Path
import fcntl
from concurrent.futures import ProcessPoolExecutor
import re

import pydicom
from pydicom.pixel_data_handlers.util import convert_color_space
import av
import numpy as np
from PIL import Image


def dictify(ds: pydicom.dataset.Dataset) -> dict:
    """Turn a pydicom Dataset into a dict with keys derived from the Element names."""
    output = dict()
    for elem in ds:
        # exclude large data value representations
        # ref: https://dicom.nema.org/medical/dicom/current/output/chtml/part05/sect_6.2.html
        if elem.VR not in {"SQ", "OB", "OW"}:
            output[elem.name] = str(elem.value)

    return output


def save_video(px, path, fps, encoding_format, encoding_args):
    container = av.open(path, mode="w")
    stream = container.add_stream(encoding_format, rate=fps)
    stream.width = px.shape[-2]
    stream.height = px.shape[-3]

    # set additional ffmpeg encoding parameters
    for k, v in encoding_args.items():
        setattr(stream, k, v)

    for ix, fr in enumerate(px):
        frame = av.VideoFrame.from_ndarray(fr, format="rgb24")
        for packet in stream.encode(frame):
            container.mux(packet)

    for packet in stream.encode():
        container.mux(packet)

    container.close()


def save_image(px, path, pil_writer_params):
    im = Image.fromarray(px)
    im.save(path, **pil_writer_params)


def process_file(file, cfg):
    print(file)
    """
    This method reads a dicom file then writes metadata and video file to disc. 
    This is intended to be used in a multiprocessing context. 
    """
    assert os.path.isfile(file), f"File does not exist: {file}"
    try:
        ds = pydicom.dcmread(file)
    except:
        print(f"Unable to read {file}. Skipping.")
        return

    # get dicom metadata and save
    metadata = dictify(ds)
    metadata["dicom_file"] = file.as_posix()

    # create video and save
    px = ds.pixel_array
    px = convert_color_space(px, ds.PhotometricInterpretation, "RGB")

    # Video media
    if int(metadata.get("Number of Frames", "1")) > 1:
        metadata["media_type"] = "video"
        if int(metadata.get("Samples per Pixel")) == 1:
            # image is grayscale. Convert to color.
            # TODO: would be better to just save as grayscale video
            px = np.stack([px, px, px], axis=-1)

        assert px.ndim == 4, f"Video pixel array has {px.ndim} dimensions. Expected 4."
        assert px.shape[-1] == 3, f"Pixel array must have 3 color channels."

        output_file_rel = file.parent / (file.stem + cfg["video"]["extension"])
        output_file = cfg["media"]["dir"] / output_file_rel
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file = output_file.as_posix()
        if not os.path.isfile(output_file) or cfg["media"]["overwrite"]:
            fps = metadata.get("Recommended Display Frame Rate", 30)
            save_video(px, output_file, fps, **cfg["video"]["save_method_kwargs"])
        else:
            print(f"File {output_file} already exists. Skipping.")

    # Image media
    else:
        metadata["media_type"] = "image"
        assert px.ndim == 3, f"Image pixel array has {px.ndim} dimensions. Expected 3."

        output_file_rel = file.parent / (file.stem + cfg["image"]["extension"])
        output_file = cfg["media"]["dir"] / output_file_rel
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file = output_file.as_posix()
        if not os.path.isfile(output_file) or cfg["media"]["overwrite"]:
            save_image(px, output_file, **cfg["image"]["save_method_kwargs"])
        else:
            print(f"File {output_file} already exists. Skipping.")

    metadata["media_file"] = output_file_rel.as_posix()

    with open(cfg["metadata"]["file"], "a") as f:
        # we lock the metadata file to allow for multiprocessing
        # a multiprocessing queue would be more efficient with greater complexity
        fcntl.lockf(f, fcntl.LOCK_EX)
        json.dump(metadata, f, sort_keys=True)
        f.write("\n")
        fcntl.lockf(f, fcntl.F_UNLCK)


def main(cfg: dict):
    # find all of the dicom files and construct metadata based on paths
    os.chdir(cfg["dicom"]["dir"])

    # get all files
    # non-dicom files are filtered by the process_file function
    matching_method = Path().rglob if cfg["dicom"]["recursive"] else Path().glob
    all_files = [f for f in matching_method("*") if f.is_file()]
    print(f"Found {len(all_files)} files in {cfg['dicom']['dir']}.")

    if cfg["num_workers"] > 0:
        # iterate over dicom files, convert and save
        with ProcessPoolExecutor(cfg["num_workers"]) as executor:
            for ix, file in enumerate(all_files):
                # if ix == 20:
                #     break
                executor.submit(process_file, file, cfg)
    else:
        for ix, file in enumerate(all_files):
            # if ix == 3:
            #     break

            process_file(file, cfg)


if __name__ == "__main__":
    parser = argparse.ArgumentParser("Export video from DICOM files.")
    parser.add_argument(
        "config", type=str, metavar="FILE", help="YAML configuration file."
    )
    args = parser.parse_args()

    # load config
    with open(args.config, "r") as f:
        cfg = yaml.safe_load(f)

    print("Running Dicom Media Exporter with configuration:")
    print("-" * 30)
    yaml.dump(cfg, sys.stdout)
    print("-" * 30)

    # save copy of config
    print(f"Saving copy of config file to {cfg['config']['file']}")
    with open(cfg["config"]["file"], "w") as f:
        yaml.dump(cfg, f)

    # throw error if not in append mode and metadata file already exists
    if (not cfg["metadata"]["append"]) and os.path.exists(cfg["metadata"]["file"]):
        raise ValueError("Cannot append to metadata file unless in append mode.")

    main(cfg)
