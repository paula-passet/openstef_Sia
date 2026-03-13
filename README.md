<!--
SPDX-FileCopyrightText: 2017-2023 Contributors to the OpenSTEF project <openstef@lfenergy.org>

SPDX-License-Identifier: MPL-2.0
-->

![OpenSTEF Logo](https://raw.githubusercontent.com/OpenSTEF/.github/main/profile/logo_openstef.png)

[![License: MPL 2.0](https://img.shields.io/badge/License-MPL_2.0-brightgreen.svg)](https://opensource.org/licenses/MPL-2.0)
[![Version](https://img.shields.io/badge/version-v.0-blue)](https://github.com/paula-passet/openstef_Sia/releases/tag/v.0)
[![CII Best Practices](https://bestpractices.coreinfrastructure.org/projects/5585/badge)](https://bestpractices.coreinfrastructure.org/projects/5585)

## What is OpenSTEF

OpenSTEF is a Python package designed for generating short-term forecasts in the energy sector. It includes all essential components required for machine learning pipelines that facilitate the forecasting process, enabling users to create accurate predictions for energy demand and supply. The package provides a flexible framework that requires users to furnish their own data storage and retrieval interface. For more information, visit the [OpenSTEF website](https://www.lfenergy.org/projects/openstef/).

## Brief Monorepo Overview

This repository contains the core OpenSTEF package with machine learning models, data processing utilities, and forecasting algorithms. The structure includes source code, documentation, examples, and testing infrastructure to support energy forecasting applications.

## How to Install

### Standard Installation

```shell
pip install openstef
```

### CPU-only Installation (Minimal XGBoost)

For x86_64 Linux and Windows platforms with smaller dependencies:

```shell
pip install openstef[cpu]
```

### Platform-specific Notes

**Windows with Conda:**
```shell
pip install pywin32==300
```

**Apple Silicon (M1/M2 Macs):**
1. Install libomp: `brew install libomp`
2. If needed, create symlink: `mkdir -p /usr/local/opt/libomp/ && ln -s /opt/brew/Cellar/libomp/{version}/lib /usr/local/opt/libomp/lib`
3. Reinstall XGBoost: `pip uninstall xgboost && conda install -c conda-forge xgboost`
4. If needed, reinstall LightGBM: `pip uninstall lightgbm && conda install -c conda-forge 'lightgbm>=4.2.0'`

## Examples

Example notebooks and tutorials are available to help you get started:

- [Offline examples repository](https://github.com/OpenSTEF/openstef-offline-example)
- [Reference implementation](https://github.com/OpenSTEF/openstef-reference)

See the `examples/` folder in this repository for additional code samples and usage demonstrations.

## License

This project is licensed under the Mozilla Public License, version 2.0 - see [LICENSE](LICENSE) for details.

Third-party libraries included in this project are licensed under their respective Open-Source licenses. SPDX-License-Identifier headers indicate applicable licenses, with license files available in the LICENSES directory.

## Contributing

We welcome contributions to OpenSTEF! Please read our contribution guidelines:

- [Code of Conduct](https://github.com/OpenSTEF/.github/blob/main/CODE_OF_CONDUCT.md)
- [Contributing Guidelines](https://github.com/OpenSTEF/.github/blob/main/CONTRIBUTING.md)
- [Project Governance](https://github.com/OpenSTEF/.github/blob/main/PROJECT_GOVERNANCE.md)

## Citations

When using OpenSTEF in your research or publications, please cite the project appropriately. Citation information and BibTeX entries are available on the [OpenSTEF documentation website](https://openstef.github.io/openstef/).

## Contact

For support, questions, or collaboration opportunities, please refer to our [Support Guidelines](https://github.com/OpenSTEF/.github/blob/main/SUPPORT.md) for information on how to connect with the OpenSTEF community.