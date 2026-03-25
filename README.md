<!--
SPDX-FileCopyrightText: 2017-2025 Contributors to the OpenSTEF project <openstef@lfenergy.org>

SPDX-License-Identifier: MPL-2.0
-->

![OpenSTEF Logo](https://raw.githubusercontent.com/OpenSTEF/openstef/main/docs/logo_openstef.png)

[![Downloads](https://static.pepy.tech/badge/openstef)](https://pepy.tech/project/openstef)
[![Downloads](https://static.pepy.tech/badge/openstef/month)](https://pepy.tech/project/openstef)
[![CII Best Practices](https://bestpractices.coreinfrastructure.org/projects/5585/badge)](https://bestpractices.coreinfrastructure.org/projects/5585)

## What is OpenSTEF

OpenSTEF is a comprehensive Python library for short-term energy forecasting that combines machine learning models, feature engineering, and evaluation tools. It provides end-to-end solutions for creating accurate probabilistic forecasts in the energy sector with a focus on modularity and type safety. Visit the [OpenSTEF website](https://openstef.github.io/openstef/) for comprehensive guides and documentation.

## Brief Monorepo Overview

OpenSTEF 4.0 uses a modular monorepo architecture with specialized packages: **openstef-core** provides data structures and utilities, **openstef-models** contains forecasting algorithms and feature engineering, **openstef-beam** offers backtesting and evaluation tools, and **openstef-meta** enables ensemble forecasting. The main **openstef** package serves as a convenient meta-package that installs core functionality.

## How to Install

### Requirements
- **Python 3.12+** (Python 3.13 supported)
- **64-bit operating system** (Windows, macOS, Linux)

### Basic Installation

```bash
# Complete OpenSTEF with core forecasting
pip install openstef

# Individual packages
pip install openstef-models  # Core forecasting only
pip install openstef-beam    # Add evaluation tools
pip install openstef-meta    # Add ensemble capabilities

# All optional features
pip install "openstef[all]"
```

### Development Installation

```bash
git clone https://github.com/OpenSTEF/openstef.git
cd openstef
uv sync --dev
```

## Examples

Explore the **[examples/](examples/)** folder for comprehensive tutorials and use cases. The examples include:

- **Quick Start**: Basic forecasting workflow
- **Model Configuration**: Customizing forecasting pipelines  
- **Benchmarking**: Comparing model performance on the Liander 2024 dataset
- **Ensemble Forecasting**: Combining multiple models for improved accuracy
- **Feature Engineering**: Advanced time series transformations

Each example includes detailed documentation and can be run independently.

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

When using OpenSTEF in academic work, please cite our project. You can generate citations in various formats:

**BibTeX:**
```bibtex
@software{openstef2025,
  title = {OpenSTEF: Open Short Term Energy Forecasting},
  author = {Alliander N.V and Contributors},
  year = {2025},
  url = {https://github.com/OpenSTEF/openstef},
  version = {4.0.0}
}
```

For additional citation formats and DOI information, visit our [project page](https://lfenergy.org/projects/openstef/).

## Contact

For questions, support, or collaboration:

- **GitHub Discussions**: [Community Q&A and discussions](https://github.com/OpenSTEF/openstef/discussions)
- **Issues**: [Bug reports and feature requests](https://github.com/OpenSTEF/openstef/issues)
- **Email**: Contact us at `openstef@lfenergy.org`
- **LF Energy**: Visit the [official project page](https://lfenergy.org/projects/openstef/)

See our [Support Guide](https://openstef.github.io/openstef/v4/project/support.html) for detailed information on getting help and community resources.