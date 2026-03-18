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

OpenSTEF is a Python package designed for generating short-term forecasts in the energy sector. It provides a complete machine learning pipeline for forecasting electricity grid load, renewable energy generation, and consumption patterns for the next hours to days. The package delivers probabilistic forecasts with automated feature engineering, data validation, and multiple fallback strategies to ensure forecast availability. For more information, visit the [OpenSTEF website](https://www.lfenergy.org/projects/openstef/).

## Brief Monorepo Overview

This repository contains the core OpenSTEF Python package with machine learning pipelines, data processing utilities, feature engineering modules, and model implementations. The package is designed to work with external data sources and can be integrated into various deployment architectures through tasks or direct pipeline usage.

## How to Install

```shell
pip install openstef
```

### Remark regarding installation within a conda environment on Windows

A version of the pywin32 package will be installed as a secondary dependency along with the installation of the openstef package. Since conda relies on an old version of pywin32, the new installation can break conda's functionality. The following command can solve this issue:

```shell
pip install pywin32==300
```

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

It is possible to install openSTEF with a minimal XGBoost (CPU-only) package. This only works on x86_64 (amd64) Linux and Windows platforms. In that case run:

```shell
pip install openstef[cpu]
```

## Examples

To help you get started, a set of fundamental example notebooks has been created. You can access these offline examples at: https://github.com/OpenSTEF/openstef-offline-example

The examples folder contains its own README with an overview of available examples covering basic usage, feature engineering, model training, and forecasting workflows.

## License

This project is licensed under the Mozilla Public License, version 2.0 - see [LICENSE](LICENSE) for details.

### Licenses third-party libraries

This project includes third-party libraries, which are licensed under their own respective Open-Source licenses. SPDX-License-Identifier headers are used to show which license is applicable. The concerning license files can be found in the LICENSES directory.

## Contributing

Please read [CODE_OF_CONDUCT.md](https://github.com/OpenSTEF/.github/blob/main/CODE_OF_CONDUCT.md), [CONTRIBUTING.md](https://github.com/OpenSTEF/.github/blob/main/CONTRIBUTING.md) and [PROJECT_GOVERNANCE.md](https://github.com/OpenSTEF/.github/blob/main/PROJECT_GOVERNANCE.md) for details on the process for submitting pull requests to us.

## Citations

For academic use, please cite OpenSTEF using the information provided on the [project website](https://www.lfenergy.org/projects/openstef/). Additional citation information and DOI references are available in the project documentation.

## Contact

Please read [SUPPORT.md](https://github.com/OpenSTEF/.github/blob/main/SUPPORT.md) for how to connect and get into contact with the OpenSTEF project. You can also join our [Teams channel](https://teams.microsoft.com/l/team/19%3ac08a513650524fc988afb296cd0358cc%40thread.tacv2/conversations?groupId=bfcb763a-3a97-4938-81d7-b14512aa537d&tenantId=697f104b-d7cb-48c8-ac9f-bd87105bafdc) for discussions and community support.