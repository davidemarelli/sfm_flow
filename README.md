
# SfM Flow

SfM Flow is a comprehensive toolset for the evaluation of 3D reconstruction pipelines. It provides tools for the creation of datasets composed by synthetic images, the execution of 3D reconstruction Structure from Motion (SfM) pipelines, and the evaluation of the obtained results. SfM Flow integrates all these features in [Blender](https://www.blender.org).

## Requirements

- [Blender](https://www.blender.org/download/releases/) 2.80.75+ &nbsp; - &nbsp; tested on Ubuntu 18.04, Windows 10 and macOS Mojave
- [ExifTool](https://exiftool.org/) v10+
- A Structure from Motion 3D reconstruction pipeline, see [pipeline support](https://github.com/davidemarelli/sfm_flow/wiki/Reconstruction-pipelines)

## Getting started

See the [Getting started](https://github.com/davidemarelli/sfm_flow/wiki/Getting-started) wiki page.

## License

[MIT License](blob/master/LICENSE)

## Documentation

Read the [wiki](https://github.com/davidemarelli/sfm_flow/wiki) for further details.

## Citation

If you use this software, please cite these papers:

```BibTeX
@article{bianco-sfm2018,
    author = {Bianco, Simone and Ciocca, Gianluigi and Marelli, Davide},
    year = {2018},
    title = {Evaluating the Performance of Structure from Motion Pipelines},
    volume = {4},
    number = {8},
    journal = {Journal of Imaging},
    doi = {10.3390/jimaging4080098},
    projectref = {http://www.ivl.disco.unimib.it/activities/evaluating-the-performance-of-structure-from-motion-pipelines/}
}
```

```BibTeX
@inproceedings{bianco2018blender-plugin,
    author = {Marelli, Davide and Bianco, Simone and Celona, Luigi and Ciocca, Gianluigi},
    year = {2018},
    pages = {1-5},
    title = {A Blender plug-in for comparing Structure from Motion pipelines},
    organization = {IEEE},
    booktitle = {2018 IEEE 8th International Conference on Consumer Electronics - Berlin (ICCE-Berlin)},
    doi = {10.1109/ICCE-Berlin.2018.8576196},
    issn = {2166-6822}
}
```
