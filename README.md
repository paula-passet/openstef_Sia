<!--
SPDX-FileCopyrightText: 2017-2025 Contributors to the OpenSTEF project <openstef@lfenergy.org>

SPDX-License-Identifier: MPL-2.0
-->

![OpenSTEF Logo](https://raw.githubusercontent.com/OpenSTEF/openstef/main/docs/source/_static/openstef-logo.png)

[![Downloads](https://static.pepy.tech/badge/openstef)](https://pepy.tech/project/openstef)
[![Downloads](https://static.pepy.tech/badge/openstef/month)](https://pepy.tech/project/openstef)
[![CII Best Practices](https://bestpractices.coreinfrastructure.org/projects/5585/badge)](https://bestpractices.coreinfrastructure.org/projects/5585)
![PyPI - License](https://img.shields.io/pypi/l/openstef)
![PyPI - Version](https://img.shields.io/pypi/v/openstef)
![Python Version](https://img.shields.io/badge/python-3.12%2B-blue)

## What is OpenSTEF

OpenSTEF is a complete toolkit for creating machine learning-powered short-term energy forecasts. It provides modular components for data processing, probabilistic forecasting models, backtesting, evaluation, and analysis to support operational decision-making in the energy sector. For more information, visit the [OpenSTEF website](https://www.lfenergy.org/projects/openstef/).

## Brief Monorepo Overview

OpenSTEF 4.0 uses a modular architecture with specialized packages: **openstef-core** provides shared types and datasets, **openstef-models** contains ML models and feature engineering, **openstef-beam** handles backtesting and evaluation, and **openstef-meta** enables ensemble forecasting. The main **openstef** package combines these components for complete functionality.

## How to Install

### Requirements
- **Python 3.12+** (Python 3.13 supported)
- **64-bit operating system** (Windows, macOS, Linux)

### Basic Installation

```bash
# For most users - includes core forecasting capabilities
pip install openstef

# Individual packages
pip install openstef-models    # ML models and feature engineering
pip install openstef-beam     # Backtesting, evaluation, analysis
pip install openstef-core     # Core utilities and datasets
pip install openstef-meta     # Ensemble forecasting

# With all optional tools
pip install "openstef[all]"
```

### Modern Package Managers

```bash
# Using uv (recommended for development)
uv add openstef

# Using conda
conda install -c conda-forge openstef
```

## Examples

Explore practical examples in the [`examples/`](examples/) folder, which contains its own README with detailed instructions for:

- **Benchmarking Examples**: Compare models using the Liander 2024 benchmark dataset
- **Configuration Examples**: Set up custom model pipelines and forecasting presets
- **Calibration Examples**: Apply isotonic quantile calibration to improve forecast reliability

## License

**Mozilla Public License Version 2.0** - see [LICENSE.md](LICENSE.md) for details.

This project includes third-party libraries licensed under their respective Open-Source licenses. SPDX-License-Identifier headers show applicable licenses. License files are in the [LICENSES/](LICENSES/) directory.
## Contributing

We welcome contributions to OpenSTEF 4.0! 

**[Read our Contributing Guide](https://openstef.github.io/openstef/v4/contribute/)** - documentation for contributors including:

- How to report bugs and suggest features
- Documentation improvements and examples
- Code contributions and development setup
- Sharing datasets and real-world use cases

### Quick Development Setup

```bash
# Clone and set up for development
git clone https://github.com/OpenSTEF/openstef.git
cd openstef
uv sync --dev

# Run tests and quality checks
uv run poe all
```

**Code of Conduct**: We follow the [Contributor Code of Conduct](https://openstef.github.io/openstef/v4/contribute/code_of_conduct.html) to ensure a welcoming environment for all contributors.
## Citations

If you use OpenSTEF in your research, please cite it as:

```bibtex
@software{openstef,
  title={OpenSTEF: Open Short Term Energy Forecasting},
  author={{Contributors to the OpenSTEF project}},
  url={https://github.com/OpenSTEF/openstef},
  version={4.0.0},
  year={2025}
}
```

## Contact

For support and questions:

- **Documentation**: [https://openstef.github.io/openstef/v4/](https://openstef.github.io/openstef/v4/)
- **GitHub Discussions**: [https://github.com/OpenSTEF/openstef/discussions](https://github.com/OpenSTEF/openstef/discussions)
- **Issue Tracker**: [https://github.com/OpenSTEF/openstef/issues](https://github.com/OpenSTEF/openstef/issues)
- **Email**: openstef@lfenergy.org
- **Support Page**: [https://openstef.github.io/openstef/v4/project/support.html](https://openstef.github.io/openstef/v4/project/support.html)