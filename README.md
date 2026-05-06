<!--
SPDX-FileCopyrightText: 2017-2023 Contributors to the OpenSTEF project <openstef@lfenergy.org>

SPDX-License-Identifier: MPL-2.0
-->

<p align="center">
  <img src="https://raw.githubusercontent.com/OpenSTEF/.github/main/profile/img/openstef_logo_wide_dark.png" alt="OpenSTEF logo" width="400"/>
</p>

<p align="center">
  <a href="https://pepy.tech/project/openstef"><img src="https://static.pepy.tech/badge/openstef" alt="Downloads"/></a>
  <a href="https://pepy.tech/project/openstef"><img src="https://static.pepy.tech/badge/openstef/month" alt="Downloads per month"/></a>
  <a href="https://bestpractices.coreinfrastructure.org/projects/5585"><img src="https://bestpractices.coreinfrastructure.org/projects/5585/badge" alt="CII Best Practices"/></a>
  <a href="https://github.com/paula-passet/openstef_Sia/releases/tag/v3.0.0"><img src="https://img.shields.io/badge/version-v3.0.0-blue" alt="Version v3.0.0"/></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MPL--2.0-green" alt="License: MPL-2.0"/></a>
</p>

---

# OpenSTEF

## What is OpenSTEF

OpenSTEF is a Python package for generating short-term energy forecasts. It provides all the components required to build end-to-end machine learning pipelines — from feature engineering and model training to hyperparameter optimisation and operational forecasting. The package supports multiple regressor backends (XGBoost, LightGBM, and others) through a unified `OpenstfRegressor` interface. Users supply their own data storage and retrieval layer; everything else is handled by the framework. For a full overview, visit the [OpenSTEF website](https://www.lfenergy.org/projects/openstef/).

## Repository Structure

| Path | Description |
|---|---|
| `openstef/` | Core library — pipelines, models, feature engineering, validation |
| `openstef/pipeline/` | Top-level pipelines: `create_forecast`, `train_model`, `optimize_hyperparameters` |
| `openstef/model/regressors/` | Regressor implementations (XGB, LGBM, quantile, linear, custom) |
| `openstef/tasks/` | Runnable task scripts for operational deployment |
| `examples/` | Self-contained usage examples — see [`examples/README.md`](examples/README.md) |
| `tests/` | Unit and integration test suite |

## Installation

Install the latest release from PyPI:

```shell
pip install openstef==3.0.0
```

**CPU-only (x86\_64 Linux / Windows only)** — installs a smaller XGBoost variant:

```shell
pip install openstef[cpu]==3.0.0
```

**conda on Windows** — a secondary `pywin32` dependency may break conda. Fix with:

```shell
pip install pywin32==300
```

See the [pywin32 README](https://github.com/mhammond/pywin32#installing-via-pip) for details.

**Apple Silicon (M1 or newer)**

1. `brew install libomp`
2. If `libomp` is not found at `/usr/local/opt`, symlink it:
   ```sh
   mkdir -p /usr/local/opt/libomp/
   ln -s /opt/brew/Cellar/libomp/{your_version}/lib /usr/local/opt/libomp/lib
   ```
3. Replace the pip-installed `xgboost` with the conda-forge build:
   ```sh
   pip uninstall xgboost && conda install -c conda-forge xgboost
   ```
4. If `lightgbm` also fails: `pip uninstall lightgbm && conda install -c conda-forge 'lightgbm>=4.2.0'`

## Examples

Ready-to-run examples are available in the [`examples/`](examples/) folder. See [`examples/README.md`](examples/README.md) for an overview of each example and what it demonstrates.

An extended set of offline notebooks is also available at [OpenSTEF/openstef-offline-example](https://github.com/OpenSTEF/openstef-offline-example).

A complete reference implementation (databases, dashboard, example data) can be found at [OpenSTEF/openstef-reference](https://github.com/OpenSTEF/openstef-reference).

## License

This project is licensed under the **Mozilla Public License, version 2.0** — see [LICENSE](LICENSE) for details.

Third-party libraries are licensed under their own respective open-source licenses. SPDX-License-Identifier headers identify the applicable license per file; corresponding license texts are in the `LICENSES/` directory.

## Contributing

Please read the following documents before opening a pull request:

- [CODE\_OF\_CONDUCT.md](https://github.com/OpenSTEF/.github/blob/main/CODE_OF_CONDUCT.md)
- [CONTRIBUTING.md](https://github.com/OpenSTEF/.github/blob/main/CONTRIBUTING.md)
- [PROJECT\_GOVERNANCE.md](https://github.com/OpenSTEF/.github/blob/main/PROJECT_GOVERNANCE.md)

## Citations

If you use OpenSTEF in your research, please cite the project via its [Linux Foundation Energy project page](https://www.lfenergy.org/projects/openstef/) or the [PyPI package page](https://pypi.org/project/openstef/). A formal BibTeX entry or DOI will be published when available.

```bibtex
@software{openstef,
  author    = {Contributors to the OpenSTEF project},
  title     = {OpenSTEF: Open Short-Term Energy Forecaster},
  version   = {3.0.0},
  url       = {https://github.com/paula-passet/openstef_Sia},
  license   = {MPL-2.0}
}
```

## Contact

Please read [SUPPORT.md](https://github.com/OpenSTEF/.github/blob/main/SUPPORT.md) for how to connect with and get support from the OpenSTEF project.