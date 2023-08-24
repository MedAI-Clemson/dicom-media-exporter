# DICOM Media Exporter

The DICOM Media Exporter (DME) tool extracts all image and video data from DICOM (.dcm) files and saves them to disc. The tool also exports all metadata contained in the dicom files in json format.

## Quick start
All of DME's settings are passed via a yaml configuration file (see `config.yml` section for details). This config includes the location of your DICOM files, where you want to save the outputs, and details about the output format. Run DME using
```
python3 dme.py config.yml
```
This command will find all DICOM files in a specified directory (optionally recursively) and will export them as media files to a specified output location. If used recursively, the file structure of the input directory will be mirrored in the output directory. 

## Features and limitations
* Tested for Ultrasound Image and Ultrasound Video DICOM files, but may work for others. Please submit an issue if you run into an unsupported DICOM type. 
* Uses multiprocessing to speed up processing. This may not work on Windows.
* Currently DICOM Media Exporter only exports still images and videos. If your application requires exporting other media types (audio for example), please submit an issue. 

## Installation

DME does not currently provide a package installation method. To install, simply clone this repository
```bash
git clone https://github.com/MedAI-Clemson/dicom-media-exporter.git
```
and install the python dependencies listed in `requirements.txt` file. Install them (in a virtual environment) using
```
python -m pip install -r requirements.txt
```
> **Note**: DME depends on FFM (see FFmpeg section below)


## config.yml
```yaml
num_workers: 4 # number of parallel processes used for the conversion. Use 0 to avoid creating child processes. 
dicom:
  dir: <input directory path> # directory containing DICOM files
  recursive: true # whether to recursively search under `dir`
media:
  dir: <output directory path> # directory to write media files
  overwrite: false # whether to overwrite existing media files with matching filepaths. Skips matching files if false.
metadata: 
  file: <output file path> # JSON-lines file (usually *.jsonl) containing DICOM metadata
  append: false # whether to append if `file` already exists. If false and `file` exists, raises an error to avoid data duplication
config: 
  file: <output file path> # location to save a copy of provided config file for reproducibility
video: 
  extension: ".mp4" # file extension for video files
  save_method_kwargs:
    encoding_format: "h264" # the encoding format passed to ffmpeg
    encoding_args: # any additional encoding options passed to ffmpeg
      pix_fmt: "yuv420p"
      options:
        crf: "17"
image:
  extension: ".png" # file extension for image files. Image encoding is inferred from extension.
  save_method_kwargs:
    pil_writer_params: {} # parameters for the Pillow image save function corresponding to `extension`
```

## Metadata fields
DME saves all DICOM fields to the provided metadata file in [JSON Lines format](https://jsonlines.org/). The resulting file will have one json object per line corresponding to a single DICOM file. These json objects contain key-value pairs representing the DICOM metadata. The key names match the full field name provided in the DICOM file which should correspond to those defined in [the DICOM standard](https://dicom.innolitics.com/ciods). 
> **Note**: DME ignores DICOM fields with [value representations](https://dicom.nema.org/medical/dicom/current/output/chtml/part05/sect_6.2.html) "SQ", "OB", and "OW". These are excluded due to their large size and because these fields usually store media, which is saved separately by DME. 

In addition to the DICOM fields, the exported metadata includes the following additional key-value pairs for linking to the input data and exported media: 
* `dicom_file`: the location of the input dicom file relative to the provided root DICOM directory.
* `media_file`: the location of the output media file relative to the provided root media directory.
* `media_type`: the type of output media, either `video` or `image`

## FFmpeg
DME uses FFmpeg to encode DICOM single- and multi-frame images as image and video files. Before using DME, FFmpeg must be installed and accessible via the `$PATH` environment variable.

There are a variety of ways to install FFmpeg:
* The [official download links](https://ffmpeg.org/download.html).
* Your package manager of choice (e.g. `sudo apt install ffmpeg` on Debian/Ubuntu, `brew install ffmpeg` on OS X, etc.).
* For [Palmetto Cluster](https://docs.rcd.clemson.edu/palmetto/about) users, FFmpeg can be loaded using `module load ffmpeg/<version>`.

Regardless of how FFmpeg is installed, you can check if your environment path is set correctly by running the `ffmpeg` command from the terminal, in which case the version information should appear, as in the following example (truncated for brevity):

```
$ ffmpeg
ffmpeg version 4.4.1 Copyright (c) 2000-2021 the FFmpeg developers
  built with gcc 9.5.0 (Spack GCC)
```

> **Note**: The actual version information displayed here may vary from one system to another; but if a message such as `ffmpeg: command not found` appears instead of the version information, FFmpeg is not properly installed.

## High priority TODO items
* Support use of Python API to export files
* Support the export of 3d data formats
* Support the export of video/3d as folders with image/slice frames
* Test on Windows machine
* Use proper logger
* Support audio export
* Support conversion of database from Orthanc server