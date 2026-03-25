<!--
SPDX-FileCopyrightText: 2017-2025 Contributors to the OpenSTEF project <openstef@lfenergy.org>

SPDX-License-Identifier: MPL-2.0
-->

![OpenSTEF Logo](https://github.com/OpenSTEF/openstef/raw/main/docs/logos/openstef-logo-color.png)

[![Downloads](https://static.pepy.tech/badge/openstef)](https://pepy.tech/project/openstef)
[![Downloads](https://static.pepy.tech/badge/openstef/month)](https://pepy.tech/project/openstef)
[![CII Best Practices](https://bestpractices.coreinfrastructure.org/projects/5585/badge)](https://bestpractices.coreinfrastructure.org/projects/5585)

## What is OpenSTEF

OpenSTEF is a comprehensive Python library for short-term energy forecasting that provides machine learning models, backtesting frameworks, and evaluation tools for creating accurate energy demand predictions. The modular architecture allows users to install only the components they need, from individual forecasting models to complete benchmarking pipelines. Learn more at the [OpenSTEF website](https://lfenergy.org/projects/openstef/).

## Brief Monorepo Overview

OpenSTEF 4.0 uses a monorepo structure with specialized packages: `openstef-core` provides shared data structures and utilities, `openstef-models` contains machine learning models and feature engineering, `openstef-beam` offers backtesting and evaluation capabilities, and `openstef-meta` provides ensemble forecasting. The root `openstef` package combines these components for a complete forecasting solution.

## How to Install

### Requirements
- **Python 3.12+** (Python 3.13 supported)
- **64-bit operating system** (Windows, macOS, Linux)

### Basic Installation

```bash
# Complete OpenSTEF suite
pip install openstef

# Core forecasting only
pip install openstef-models

# With all optional components
pip install "openstef[all]"
```

### Package Options

| Package | Purpose | Install Command |
|---------|---------|-----------------|
| **openstef** | Meta-package with core components | `pip install openstef` |
| **openstef-models** | ML models, feature engineering, data processing | `pip install openstef-models` |
| **openstef-beam** | Backtesting, Evaluation, Analysis, Metrics | `pip install openstef-beam` |
| **openstef-core** | Core utilities, dataset types, shared infrastructure | `pip install openstef-core` |
| **openstef-meta** | Ensemble forecasting and model combination | `pip install openstef-meta` |

### Modern Package Managers

```bash
# Using uv (recommended for development)
uv add openstef

# Using conda
conda install -c conda-forge openstef
```

## Examples

Explore practical examples in the [examples/](examples/) folder, which contains its own README with detailed guidance on:

- **Forecasting workflows**: Complete end-to-end forecasting pipelines
- **Benchmarking**: Comparing model performance with the Liander 2024 dataset
- **Feature engineering**: Creating and configuring custom transforms
- **Model calibration**: Improving forecast uncertainty with isotonic regression

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

To cite OpenSTEF in academic work, please use:

```bibtex
@software{openstef,
  title = {{OpenSTEF}: Open Short Term Energy Forecasting},
  author = {{Contributors to the OpenSTEF project}},
  url = {https://github.com/OpenSTEF/openstef},
  version = {4.0.0},
  year = {2025}
}
```

For more citation formats and DOI links, visit our [project homepage](https://lfenergy.org/projects/openstef/).

## Contact

- **Documentation**: [OpenSTEF Documentation](https://openstef.github.io/openstef/v4/)
- **Support**: [Support Guide](https://openstef.github.io/openstef/v4/project/support.html)
- **Community**: [GitHub Discussions](https://github.com/OpenSTEF/openstef/discussions)
- **Issues**: [GitHub Issues](https://github.com/OpenSTEF/openstef/issues)
- **Email**: `openstef@lfenergy.org`