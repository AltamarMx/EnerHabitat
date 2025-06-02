# EnerHabitat
### Tools for evaluating the thermal performance of structures based on EPW files

## Table of contents
- [EnerHabitat](#enerhabitat)
    - [Tools for evaluating the thermal performance of structures based on EPW files](#tools-for-evaluating-the-thermal-performance-of-structures-based-on-epw-files)
  - [Table of contents](#table-of-contents)
  - [Getting started](#getting-started)
    - [Installation](#installation)
    - [Folder structure](#folder-structure)
  - [Main functions](#main-functions)
    - [meanDay](#meanday)
    - [Tsa](#tsa)
    - [solveCS](#solvecs)
  - [Materials](#materials)
  - [Other parameters](#other-parameters)
  - [Dependencies](#dependencies)
  - [License](#license)

## Getting started
**enerhabitat** is a Python package for thermal simulation of constructive systems based on meteorological data from EPW files. The values that are calculated include:

- Ta  : Ambient temperature
- Tsa : Sun-Air temperature
- Ti  : Interior temperature
- Ig  : Global irradiance
- Ib  : Beam irradiance
- Id  : Diffuse irradiance
- Is  : Surface irradiance

### Installation

The source code is currently hosted on GitHub at [eh_development](https://github.com/AltamarMx/eh_development)

Binary installers for the latest released version are available at the Test Python Package Index [TestPyPI](https://test.pypi.org/project/enerhabitat) 

```bash
pip install -i https://test.pypi.org/simple/ enerhabitat
```

If you're working with the [uv](https://docs.astral.sh/uv/) Python package manager you can use the following

```bash
$ uv pip install --index-url https://test.pypi.org/simple/ enerhabitat
```

### Folder structure

The following shows basic folder structure
```
├── main.py
├── materials.ini   # Materials properties
└── epw
    ├── ...
    └── example_file.epw
```

## Main functions
### meanDay
Calculates the ambient temperature, global, beam and diffuse irradiance per second for the average day based on EPW file
```python
import enerhabitat as eh

dia_promedio = eh.meanDay(epw_file = "epw/example_file.epw")
```

The output data frame should have the following structure

time | zenith | elevation | azimuth | equation_of_time | Ta | Ig | Ib | Id |Tn | DeltaTn
:---: | :---: | :---: | :---: | :---: |:---: | :---: | :---: | :---: | :---: | :---:
 ... | ... | ... | ... | ... | ... | ... | ... | ... | ... | ...

### Tsa

Calculates the sun-air temperature and solar irradiance per second for the average day

```python
import enerhabitat as eh

sun_air = eh.Tsa(
    dia_promedio,           # DataFrame with Ib, Ig, Id
    solar_absortance = 0.8, # Surface color
    surface_tilt = 90,      # 90 = vertical
    surface_azimuth = 90    # 0 = North, 90 = East
)

```

### solveCS
Solves the constructive system's inside temperature for a Tsa simulation dataframe

```python
import enerhabitat as eh

# list of tuples from outside to inside with material and width
constructive_system = [
    ("material_1" , L_1),
    ("material_n", L_n)
]

interior = eh.solveCS(
    constructive_system,  
    sun_air_df      # DataFrame with Tn, Ta, Tsa
    )

```

## Materials

The materials and their properties are specified in the `materials.ini` configuration file, specifying the material name as the `key` and its values ​​for `k`, `rho` and `c`

```ini
[concrete]
k   = 1.35  # Overall heat transfer coefficient
rho = 1800  # Density
c   = 1000  # Specific heat

[adobe]
k   = 0.58
rho = 1500
c   = 1480
```

To set a configuration file, use the `materials()` function and specify the `path`

```python
import enerhabitat as eh

eh.materials("./config/new_materials.ini")
```
```shell
>>> "./config/new_materials.ini"
```

## Other parameters
You can set various configuration values ​​to modify the behavior of the calculations

```python
import enerhabitat as eh

eh.La = 2.5
eh.Nx = 20     # Number of elements to discretize
eh.ho = 13     # Outside convection heat transfer
eh.hi = 8.6    # Inside convection heat transfer
eh.dt = 60
```

## Dependencies
- [numba](https://numba.pydata.org/)
- [pvlib](https://pvlib-python.readthedocs.io/en/stable/)
- [numpy](https://numpy.org/)
- [pandas](https://pandas.pydata.org/)
- [pytz](https://pypi.org/project/pytz/)


## License
Code released under the [MIT license](https://github.com/AltamarMx/eh_development/blob/main/LICENSE).