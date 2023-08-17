import os
import yaml
import json
import argparse
import sys
from pathlib import Path
import fcntl
from concurrent.futures import ProcessPoolExecutor

import pydicom
from pydicom.pixel_data_handlers.util import convert_color_space
import av
import numpy as np


def dictify(ds: pydicom.dataset.Dataset) -> dict:
    """Turn a pydicom Dataset into a dict with keys derived from the Element names."""
    output = dict()
    for elem in ds:
        # exclude large data value representations
        # ref: https://dicom.nema.org/medical/dicom/current/output/chtml/part05/sect_6.2.html
        if elem.VR not in {"SQ", "OB", "OW"}:
            output[elem.name] = str(elem.value)

    return output

def save_video(px, path, fps, stream_format, stream_args):
    container = av.open(path, mode='w')
    stream = container.add_stream(stream_format, rate=fps)
    stream.width = px.shape[-2]
    stream.height = px.shape[-3]
    
    for k, v in stream_args.items():
        setattr(stream, k, v)
    
    for ix, fr in enumerate(px):
        frame = av.VideoFrame.from_ndarray(fr, format='rgb24')
        for packet in stream.encode(frame):
            container.mux(packet)
            
    for packet in stream.encode():
        container.mux(packet)
    
    container.close()
    

def process_file(file, cfg):
    print(file)
    """
    This method reads a dicom file then writes metadata and video file to disc. 
    This is intended to be used in a multiprocessing context. 
    """
    assert os.path.isfile(file), f"File does not exist: {file}"
    
    ds = pydicom.dcmread(file)
    
    # get dicom metadata and save
    metadata = dictify(ds)
        
    # create video and save
    px = ds.pixel_array
    px = convert_color_space(px, ds.PhotometricInterpretation, 'RGB')
    
    if int(metadata.get('Number of Frames', '1')) > 1:
        if px.ndim == 3:
            print(f"DICOM file {file.as_posix()} contains a grayscale video. Converting to color.")
            px = np.stack([px, px, px], axis=-1)        
        
        assert px.ndim == 4, f"Pixel array has {px.ndim} dimensions. Expected 4."
        assert px.shape[-1] == 3, f"Pixel array must have 3 color channels."
        
        output_file = cfg['output']['dir'] / file.parent / (file.stem + '.mp4')
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file = output_file.as_posix()
        if not os.path.isfile(output_file):
            fps = metadata.get('Recommended Display Frame Rate', 30)  
            save_video(px, output_file, fps, 
                    cfg['output']['stream_format'],
                    cfg['output']['stream_args'])
        else:
            print(f"File {output_file} already exists. Skipping.")
        
        metadata['video_file_path'] = output_file
        
    with open(cfg['output']['metadata_file'], 'a') as f:
        # we lock the metadata file to allow for multiprocessing
        # a multiprocessing queue would be more efficient with greater complexity
        fcntl.lockf(f, fcntl.LOCK_EX)
        json.dump(metadata, f, sort_keys=True)
        f.write("\n")
        fcntl.lockf(f, fcntl.F_UNLCK)


def main(cfg: dict):
    # find all of the dicom files and construct metadata based on paths
    cwd = os.getcwd()
    os.chdir(cfg["input"]["dir"])
    dicom_files = list(Path().rglob("*.dcm"))
    
    # for ix, file in enumerate(dicom_files):
    #     if ix==10:
    #         break
        
    #     process_file(file, cfg)
    
    # iterate over dicom files, convert and save
    with ProcessPoolExecutor(cfg['num_workers']) as executor:
        for ix, file in enumerate(dicom_files):
            # if ix==10:
            #     break
            
            executor.submit(process_file, file, cfg)
            
            
        

if __name__ == "__main__":

    parser = argparse.ArgumentParser("Export video from DICOM files.")
    parser.add_argument(
        "config", type=str, metavar="FILE", help="YAML configuration file."
    )
    parser.add_argument(
        "--overwrite", action='store_true', default=False, 
        help="Overwrite existing metadata file. Otherwise throws an error if metadata already exists."
    )
    args = parser.parse_args()
    
    # load config
    with open(args.config, "r") as f:
        cfg = yaml.safe_load(f)
        
    print("Running DCM2VID with configuration:")
    print("-" * 30)
    yaml.dump(cfg, sys.stdout)
    print("-" * 30)
    
    # safety checks
    if args.overwrite:
        if os.path.isfile(cfg['output']['metadata_file']):
            os.remove(cfg['output']['metadata_file'])
    else:
        if not args.overwrite:
            assert not os.path.isfile(cfg['output']['metadata_file']), \
                "Metadata file already exists. Use --overwrite if you intend to overwrite records."
    # TODO: implement append mode
    
    main(cfg)