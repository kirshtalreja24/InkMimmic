# AI Handwriter Project

This folder contains the work completed so far for a handwriting-segmentation project that turns handwriting pages into individual character PNGs and a CSV manifest.

## What has been done

- Implemented a preprocessing pipeline in [testa.py](testa.py) for:
  - loading the input image,
  - converting to grayscale,
  - applying Gaussian blur,
  - using Sauvola adaptive thresholding,
  - removing ruled-line artifacts,
  - applying morphological cleanup.
- Implemented character component detection using contour-based segmentation.
- Added logic to merge tiny fragments such as dots or crossbars into nearby character boxes.
- Added line and word grouping based on character positions and spacing.
- Added image export logic to save each detected character as a transparent PNG with an alpha mask.
- Generated a manifest file describing each extracted character image.

## Project files

- [testa.py](testa.py) — main pipeline script for preprocessing, segmentation, and export.
- [chars3/manifest.csv](chars3/manifest.csv) — manifest with extracted character metadata.
- [chars3/](chars3/) — folder containing generated character PNGs.
- [data/](data/) — input data folders for the handwriting samples.

## Current output

The current run generated 58 character images and wrote 58 manifest rows.

## How to run

From this folder, run:

```bash
python testa.py --input <path-to-image> --output_dir chars3
```

## Notes

- The exported PNGs are saved as transparent images with the ink mask stored in the alpha channel.
- The metadata in [chars3/manifest.csv](chars3/manifest.csv) includes the filename, line, word, character index, and bounding box coordinates.
