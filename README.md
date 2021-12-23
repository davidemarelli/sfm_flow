
# SfM Flow

SfM Flow is a comprehensive toolset for the evaluation of 3D reconstruction pipelines. It provides tools for the creation of datasets composed by synthetic images, the execution of 3D reconstruction Structure from Motion (SfM) pipelines, and the evaluation of the obtained results. SfM Flow integrates all these features in [Blender](https://www.blender.org).

Read more in the paper [*SfM Flow*: A comprehensive toolset for the evaluation of 3D reconstruction pipelines](http://doi.org/10.1016/j.softx.2021.100931) by [Davide Marelli](http://www.ivl.disco.unimib.it/people/davide-marelli/), [Simone Bianco](http://www.ivl.disco.unimib.it/people/simone-bianco/) and [Gianluigi Ciocca](http://www.ivl.disco.unimib.it/people/gianluigi-ciocca/).

## Requirements

- [Blender](https://www.blender.org/download/releases/) 2.80.75 or later ([Blender 2.93 LTS](https://www.blender.org/download/lts/2-93/) recommended) &nbsp; - &nbsp; tested on Ubuntu 18.04, Windows 10 and macOS Mojave
- [ExifTool](https://exiftool.org/) v10 or later
- A Structure from Motion 3D reconstruction pipeline, see [pipeline support](https://github.com/davidemarelli/sfm_flow/wiki/Reconstruction-pipelines)

## Getting started

See the [Getting started](https://github.com/davidemarelli/sfm_flow/wiki/Getting-started) wiki page.

## License

[MIT License](LICENSE)

## Documentation

Read the [wiki](https://github.com/davidemarelli/sfm_flow/wiki) for further details.

## Citation

If you use this software, please cite these papers:

```BibTeX
@article{marelli2022sfmflow,
    author = {Marelli, Davide and Bianco, Simone and Ciocca Gianluigi},
    year = {2022},
    pages = {100931},
    title = {SfM Flow: A comprehensive toolset for the evaluation of 3D reconstruction pipelines},
    volume = {17},
    journal = {SoftwareX},
    doi = {10.1016/j.softx.2021.100931},
    issn = {2352-7110},
    projectref = {http://www.ivl.disco.unimib.it/activities/evaluating-the-performance-of-structure-from-motion-pipelines/}
}
```

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
