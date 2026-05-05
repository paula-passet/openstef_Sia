<!--
SPDX-FileCopyrightText: 2017-2023 Contributors to the OpenSTEF project <openstef@lfenergy.org>

SPDX-License-Identifier: MPL-2.0
-->

<p align="center">
  <img src="https://raw.githubusercontent.com/OpenSTEF/.github/main/profile/img/openstef_logo_wide_dark.svg" alt="OpenSTEF logo" width="400"/>
</p>

<p align="center">
  <a href="https://pepy.tech/project/openstef"><img src="https://static.pepy.tech/badge/openstef" alt="Downloads"/></a>
  <a href="https://pepy.tech/project/openstef"><img src="https://static.pepy.tech/badge/openstef/month" alt="Downloads per month"/></a>
  <a href="https://bestpractices.coreinfrastructure.org/projects/5585"><img src="https://bestpractices.coreinfrastructure.org/projects/5585/badge" alt="CII Best Practices"/></a>
  <a href="https://github.com/paula-passet/openstef_Sia/releases/tag/v3.0.0"><img src="https://img.shields.io/badge/version-v3.0.0-blue" alt="Version v3.0.0"/></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MPL--2.0-green" alt="License: MPL-2.0"/></a>
</p>

---

## What is OpenSTEF

OpenSTEF is a Python package designed for generating short-term forecasts in the energy sector. It provides all the essential components of an end-to-end machine learning pipeline — from feature engineering and model training to hyperparameter optimisation and operational forecasting. Models are built on industry-standard regressors (XGBoost, LightGBM, and others) that implement a common `OpenstfRegressor` interface. To use the package, users supply their own data storage and retrieval interface; for more information visit the [OpenSTEF website](https://www.lfenergy.org/projects/openstef/).

---

## Repository Overview

The repository is organised as a single Python package (`openstef/`) with the following top-level areas:

| Path | Purpose |
|---|---|
| `openstef/pipeline/` | High-level pipelines: create forecast, train model, optimise hyperparameters |
| `openstef/model/` | Regressor implementations (XGB, LGBM, quantile variants) and serialisation via MLflow |
| `openstef/feature_engineering/` | Feature applicators and general feature helpers |
| `openstef/model_selection/` | Cross-validation and train/validation/test splitting utilities |
| `openstef/tasks/` | Runnable task entry points (forecast, train, KPI calculation, etc.) |
| `openstef/data_classes/` | Typed data classes (`PredictionJobDataClass`, `ModelSpecificationDataClass`) |
| `examples/` | Self-contained example scripts — see [`examples/README.md`](examples/README.md) |

---

## How to Install

**Standard install (recommended):**

```shell
pip install openstef
```

**CPU-only / minimal XGBoost install** *(x86\_64 Linux and Windows only — significantly smaller dependency footprint):*

```shell
pip install openstef[cpu]
```

**Platform notes:**

- **conda on Windows** — A secondary `pywin32` dependency may break conda. Fix with:
  ```shell
  pip install pywin32==300
  ```
  See the [pywin32 README](https://github.com/mhammond/pywin32#installing-via-pip) for details.

- **Apple Silicon (M1/M2)** — Install `libomp` via Homebrew first (`brew install libomp`), then reinstall `xgboost` and, if needed, `lightgbm` via `conda-forge`:
  ```shell
  conda install -c conda-forge xgboost
  conda install -c conda-forge 'lightgbm>=4.2.0'
  ```

---

## Examples

Ready-to-run examples are located in the [`examples/`](examples/) folder. See [`examples/README.md`](examples/README.md) for an overview of all available examples.

An extended set of offline example notebooks is also available at [github.com/OpenSTEF/openstef-offline-example](https://github.com/OpenSTEF/openstef-offline-example).

A complete reference implementation — including databases, a live dashboard, and example data — is available at [github.com/OpenSTEF/openstef-reference](https://github.com/OpenSTEF/openstef-reference).

---

## License

This project is licensed under the **Mozilla Public License, version 2.0** — see [LICENSE](LICENSE) for details.

Third-party libraries are licensed under their own respective open-source licenses. SPDX-License-Identifier headers are used throughout the source; corresponding license texts are in the `LICENSES/` directory.

---

## Contributing

Please read the following documents before submitting a pull request:

- [CODE\_OF\_CONDUCT.md](https://github.com/OpenSTEF/.github/blob/main/CODE_OF_CONDUCT.md)
- [CONTRIBUTING.md](https://github.com/OpenSTEF/.github/blob/main/CONTRIBUTING.md)
- [PROJECT\_GOVERNANCE.md](https://github.com/OpenSTEF/.github/blob/main/PROJECT_GOVERNANCE.md)

---

## Citations

If you use OpenSTEF in your research, please cite the project. The recommended citation and any associated DOI can be found on the [OpenSTEF documentation site](https://openstef.github.io/openstef/index.html) and the [Linux Foundation Energy project page](https://www.lfenergy.org/projects/openstef/).

```bibtex
@software{openstef,
  author    = {Contributors to the OpenSTEF project},
  title     = {OpenSTEF: Open Short-Term Energy Forecaster},
  version   = {v3.0.0},
  url       = {https://github.com/paula-passet/openstef_Sia},
  license   = {MPL-2.0}
}
```

---

## Contact

Please read [SUPPORT.md](https://github.com/OpenSTEF/.github/blob/main/SUPPORT.md) for how to connect with and get support from the OpenSTEF project community.