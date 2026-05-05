<!--
SPDX-FileCopyrightText: 2017-2023 Contributors to the OpenSTEF project <openstef@lfenergy.org>

SPDX-License-Identifier: MPL-2.0
-->

<p align="center">
  <img src="https://raw.githubusercontent.com/OpenSTEF/.github/main/profile/img/openstef_logo_wide_colorful_bg.png" alt="OpenSTEF Logo" width="400"/>
</p>

<p align="center">
  <a href="https://pepy.tech/project/openstef"><img src="https://static.pepy.tech/badge/openstef" alt="Downloads"/></a>
  <a href="https://pepy.tech/project/openstef"><img src="https://static.pepy.tech/badge/openstef/month" alt="Downloads per month"/></a>
  <a href="https://bestpractices.coreinfrastructure.org/projects/5585"><img src="https://bestpractices.coreinfrastructure.org/projects/5585/badge" alt="CII Best Practices"/></a>
  <a href="https://github.com/paula-passet/openstef_Sia/releases/tag/v3.0.0"><img src="https://img.shields.io/badge/version-v3.0.0-blue" alt="Version v3.0.0"/></a>
  <a href="https://github.com/paula-passet/openstef_Sia/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MPL--2.0-green" alt="License: MPL-2.0"/></a>
</p>

---

## What is OpenSTEF

OpenSTEF is a Python package for generating short-term energy forecasts, providing all the essential components of an end-to-end machine learning pipeline — from feature engineering and model training to forecast creation and KPI monitoring. It supports multiple model backends (XGBoost, LightGBM, and others) through a unified `OpenstfRegressor` interface, and is designed to integrate with any data storage layer you supply. OpenSTEF is a [Linux Foundation Energy](https://www.lfenergy.org/projects/openstef/) project. For full documentation, visit [openstef.github.io/openstef](https://openstef.github.io/openstef/index.html).

---

## Repository Structure

The repository is organised as a single-package library with the following top-level directories:

| Path | Purpose |
|---|---|
| `openstef/` | Core library — pipelines, models, feature engineering, tasks, data classes |
| `test/` | Unit and integration tests |
| `examples/` | Runnable example scripts and notebooks |
| `docs/` | Source files for the documentation website |
| `LICENSES/` | License files for third-party dependencies |

---

## Installation

Install the latest release from PyPI:

```shell
pip install openstef==3.0.0
```

**CPU-only (x86\_64 Linux / Windows only)** — installs a smaller XGBoost variant:

```shell
pip install openstef[cpu]==3.0.0
```

### conda on Windows

A secondary `pywin32` dependency may break conda. Fix with:

```shell
pip install pywin32==300
```

See the [pywin32 README](https://github.com/mhammond/pywin32#installing-via-pip) for details.

### Apple Silicon (M1 and later)

1. `brew install libomp`
2. If `libomp` is not found at `/usr/local/opt`, symlink it:
   ```sh
   mkdir -p /usr/local/opt/libomp/
   ln -s /opt/brew/Cellar/libomp/{your_version}/lib /usr/local/opt/libomp/lib
   ```
3. Reinstall XGBoost via conda-forge: `pip uninstall xgboost && conda install -c conda-forge xgboost`
4. If LightGBM also fails: `pip uninstall lightgbm && conda install -c conda-forge 'lightgbm>=4.2.0'`

---

## Examples

Runnable examples are in the [`examples/`](https://github.com/paula-passet/openstef_Sia/tree/v3.0.0/examples) folder. See the [`examples/README.md`](https://github.com/paula-passet/openstef_Sia/tree/v3.0.0/examples/README.md) for an overview of available scripts and notebooks.

For a fully self-contained offline walkthrough, see the [openstef-offline-example](https://github.com/OpenSTEF/openstef-offline-example) repository.

A complete reference implementation (databases, dashboard, example data) is available at [openstef-reference](https://github.com/OpenSTEF/openstef-reference).

---

## License

This project is licensed under the **Mozilla Public License, version 2.0** — see [`LICENSE`](https://github.com/paula-passet/openstef_Sia/blob/main/LICENSE) for details.

Third-party libraries are licensed under their own respective open-source licenses. SPDX-License-Identifier headers are used throughout the codebase; corresponding license texts are in the [`LICENSES/`](https://github.com/paula-passet/openstef_Sia/tree/main/LICENSES) directory.

---

## Contributing

Please read the following documents before submitting a pull request:

- [CODE\_OF\_CONDUCT.md](https://github.com/OpenSTEF/.github/blob/main/CODE_OF_CONDUCT.md)
- [CONTRIBUTING.md](https://github.com/OpenSTEF/.github/blob/main/CONTRIBUTING.md)
- [PROJECT\_GOVERNANCE.md](https://github.com/OpenSTEF/.github/blob/main/PROJECT_GOVERNANCE.md)

---

## Citations

If you use OpenSTEF in your research, please cite the project via its [Linux Foundation Energy project page](https://www.lfenergy.org/projects/openstef/) or the [PyPI package](https://pypi.org/project/openstef/). A suggested BibTeX entry:

```bibtex
@software{openstef,
  author    = {Contributors to the OpenSTEF project},
  title     = {OpenSTEF: Open Short-Term Energy Forecasting},
  version   = {3.0.0},
  year      = {2023},
  url       = {https://github.com/paula-passet/openstef_Sia},
  license   = {MPL-2.0}
}
```

---

## Contact

Please read [SUPPORT.md](https://github.com/OpenSTEF/.github/blob/main/SUPPORT.md) for how to connect with and get support from the OpenSTEF project community.