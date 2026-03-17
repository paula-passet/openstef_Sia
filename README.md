<!--
SPDX-FileCopyrightText: 2017-2023 Contributors to the OpenSTEF project <openstef@lfenergy.org>

SPDX-License-Identifier: MPL-2.0
-->

# OpenSTEF

<!-- Badges -->
[![Downloads](https://static.pepy.tech/badge/openstef)](https://pepy.tech/project/openstef)
[![Downloads](https://static.pepy.tech/badge/openstef/month)](https://pepy.tech/project/openstef)
[![CII Best Practices](https://bestpractices.coreinfrastructure.org/projects/5585/badge)](https://bestpractices.coreinfrastructure.org/projects/5585)

## What is OpenSTEF

OpenSTEF is a Python package designed for generating short-term forecasts in the energy sector. It provides a complete machine learning pipeline that includes data validation, feature engineering, model training, and probabilistic forecasting for energy grid load predictions. The package enables automated forecasting of energy consumption, renewable generation, or combinations thereof for the next hours to days.

For more information, visit the [OpenSTEF website](https://www.lfenergy.org/projects/openstef/).

## Brief Monorepo Overview

This repository contains the core OpenSTEF package with modular components for machine learning pipelines, feature engineering, model training, and forecasting. The package is designed to work with external data storage and retrieval interfaces, making it adaptable to different IT environments.

## How to Install

### Install the openstef package

```shell
pip install openstef
```

### Remark regarding installation within a **conda environment on Windows**

A version of the pywin32 package will be installed as a secondary dependency along with the installation of the openstef package. Since conda relies on an old version of pywin32, the new installation can break conda's functionality. The following command can solve this issue:

```shell
pip install pywin32==300
```

For more information on this issue see the [readme of pywin32](https://github.com/mhammond/pywin32#installing-via-pip) or [this Github issue](https://github.com/mhammond/pywin32/issues/1865#issue-1212752696).

### Remark regarding installation on Apple Silicon

If you want to install the `openstef` package on Apple Silicon (Mac with M1-chip or newer), you can encounter issues with the dependencies, such as `xgboost`. Solution:

1. Run `brew install libomp` (if you haven't installed Homebrew: [follow instructions here](https://brew.sh/))
2. If your interpreter can not find the `libomp` installation in `/usr/local/bin`, it is probably in `/opt/brew/Cellar`. Run:

```sh
mkdir -p /usr/local/opt/libomp/
ln -s /opt/brew/Cellar/libomp/{your_version}/lib /usr/local/opt/libomp/lib
```

3. Uninstall `xgboost` with `pip` (`pip uninstall xgboost`) and install with `conda-forge` (`conda install -c conda-forge xgboost`)
4. If you encounter similar issues with `lightgbm`: uninstall `lightgbm` with `pip` (`pip uninstall lightgbm`) and install later version with `conda-forge` (`conda install -c conda-forge 'lightgbm>=4.2.0'`)

### Remark regarding installation with minimal XGBoost dependency

It is possible to install openSTEF with a minimal XGBoost (CPU-only) package. This only works on x86_64 (amd64) Linux and Windows platforms. Advantage is that significantly smaller dependencies are installed. In that case run:

```shell
pip install openstef[cpu]
```

## Examples

To help you get started, a set of fundamental example notebooks has been created. You can access these offline examples in the [openstef-offline-example repository](https://github.com/OpenSTEF/openstef-offline-example).

The examples folder contains practical demonstrations of how to use OpenSTEF for various forecasting tasks and workflows.

## License

This project is licensed under the Mozilla Public License, version 2.0 - see [LICENSE](LICENSE) for details.

### Licenses third-party libraries

This project includes third-party libraries, which are licensed under their own respective Open-Source licenses. SPDX-License-Identifier headers are used to show which license is applicable. The concerning license files can be found in the LICENSES directory.

## Contributing

Please read [CODE_OF_CONDUCT.md](https://github.com/OpenSTEF/.github/blob/main/CODE_OF_CONDUCT.md), [CONTRIBUTING.md](https://github.com/OpenSTEF/.github/blob/main/CONTRIBUTING.md) and [PROJECT_GOVERNANCE.md](https://github.com/OpenSTEF/.github/blob/main/PROJECT_GOVERNANCE.md) for details on the process for submitting pull requests to us.

## Citations

For academic use, please cite OpenSTEF appropriately. Citation information and BibTeX entries are available in the [project documentation](https://openstef.github.io/openstef/).

## Contact

Please read [SUPPORT.md](https://github.com/OpenSTEF/.github/blob/main/SUPPORT.md) for how to connect and get into contact with the OpenSTEF project.