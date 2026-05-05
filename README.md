<!--
SPDX-FileCopyrightText: 2017-2025 Contributors to the OpenSTEF project <openstef@lfenergy.org>

SPDX-License-Identifier: MPL-2.0
-->

<p align="center">
  <img src="https://raw.githubusercontent.com/OpenSTEF/.github/main/profile/img/openstef_logo_wide_colorful_bg.png" alt="OpenSTEF logo" width="400"/>
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

## What is OpenSTEF?

**OpenSTEF** (Open Short-Term Energy Forecasting) is a model-agnostic Python framework for generating short-term energy forecasts hours to days ahead. It provides complete machine learning pipelines covering data preprocessing, feature engineering, model training, probabilistic forecasting, evaluation, and post-processing. OpenSTEF includes built-in domain knowledge for energy-specific use cases such as congestion management, transport forecasting, EV charging capacity estimation, and grid loss prediction. For more information, visit the [OpenSTEF website](https://www.lfenergy.org/projects/openstef/) and the [documentation](https://openstef.github.io/openstef/index.html).

---

## Repository Structure

This repository is organised as a **modular monorepo** containing four self-contained packages that can be installed independently or together:

| Package | Description |
|---|---|
| [`openstef-core`](packages/openstef-core) | Data types, interfaces, base classes, and shared utilities — the foundation for all other packages |
| [`openstef-models`](packages/openstef-models) | Forecasting models, preprocessing pipelines, energy-specific transformations, explainability, and presets |
| [`openstef-meta`](packages/openstef-meta) | Meta-learning: modern ensemble models and advanced model architectures |
| [`openstef-beam`](packages/openstef-beam) | **B**acktesting, **E**valuation, **A**nalysis, and **M**etrics — regression testing and benchmarking |

---

## Installation

**Requirements:** Python ≥ 3.12, < 4.0

Install the complete framework with a single command:

```bash
pip install openstef
```

This meta-package installs `openstef-core`, `openstef-models`, `openstef-meta`, and `openstef-beam`.

### Install individual packages

```bash
pip install openstef-core
pip install openstef-models
pip install openstef-beam
pip install openstef-meta
```

### Optional extras

```bash
# LightGBM support
pip install openstef-models[lgbm]

# CPU-only XGBoost (Linux/Windows x86_64)
pip install openstef-models[xgb-cpu]

# GPU XGBoost
pip install openstef-models[xgb-gpu]

# openstef-beam with all extras (includes baselines and S3 support)
pip install openstef-beam[all]
```

> **Apple Silicon (M1+):** If you encounter issues with `xgboost` or `lightgbm`, uninstall via `pip` and reinstall using `conda install -c conda-forge xgboost` / `conda install -c conda-forge 'lightgbm>=4.6.0'`. You may also need to run `brew install libomp` first.

---

## Examples

Ready-to-run examples are available in the [`examples/`](examples/) folder. See [`examples/README.md`](examples/README.md) for an overview of all available examples and setup instructions.

---

## License

This project is licensed under the **Mozilla Public License, version 2.0** — see [`LICENSE`](LICENSE) for details.

Third-party libraries are licensed under their own respective open-source licenses. SPDX-License-Identifier headers indicate the applicable license per file; corresponding license texts are in the [`LICENSES/`](LICENSES/) directory.

---

## Contributing

Please read the following documents before submitting a pull request:

- [CODE_OF_CONDUCT.md](https://github.com/OpenSTEF/.github/blob/main/CODE_OF_CONDUCT.md)
- [CONTRIBUTING.md](https://github.com/OpenSTEF/.github/blob/main/CONTRIBUTING.md)
- [PROJECT_GOVERNANCE.md](https://github.com/OpenSTEF/.github/blob/main/PROJECT_GOVERNANCE.md)

---

## Citations

If you use OpenSTEF in your research, please cite the project. A BibTeX entry and DOI reference are available on the [Linux Foundation Energy project page](https://www.lfenergy.org/projects/openstef/) and the [OpenSTEF documentation site](https://openstef.github.io/openstef/index.html).

---

## Contact

Please read [SUPPORT.md](https://github.com/OpenSTEF/.github/blob/main/SUPPORT.md) for how to connect with and get support from the OpenSTEF project community.