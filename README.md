<!--
SPDX-FileCopyrightText: 2017-2025 Contributors to the OpenSTEF project <openstef@lfenergy.org>

SPDX-License-Identifier: MPL-2.0
-->

![OpenSTEF Logo](https://raw.githubusercontent.com/OpenSTEF/openstef/main/docs/source/_static/logo-color.png)

[![Downloads](https://static.pepy.tech/badge/openstef)](https://pepy.tech/project/openstef)
[![Downloads](https://static.pepy.tech/badge/openstef/month)](https://pepy.tech/project/openstef)
[![CII Best Practices](https://bestpractices.coreinfrastructure.org/projects/5585/badge)](https://bestpractices.coreinfrastructure.org/projects/5585)
[![License: MPL 2.0](https://img.shields.io/badge/License-MPL%202.0-brightgreen.svg)](https://opensource.org/licenses/MPL-2.0)

## What is OpenSTEF

**OpenSTEF** is a modular framework for short-term energy forecasting that provides machine learning models, backtesting capabilities, and evaluation tools. OpenSTEF 4.0 introduces a complete architectural refactor with enhanced modularity, type safety, and modern Python development practices. Visit the [OpenSTEF website](https://lfenergy.org/projects/openstef/) for more information.

## Brief Monorepo Overview

OpenSTEF 4.0 uses a modular monorepo structure with specialized packages:

- **`openstef`** - Meta-package combining core forecasting functionality
- **`openstef-models`** - ML models, feature engineering, and data processing  
- **`openstef-beam`** - Backtesting, Evaluation, Analysis, and Metrics framework
- **`openstef-core`** - Core utilities, dataset types, and base models
- **`openstef-meta`** - Ensemble forecasting and meta-models

Each package can be installed independently based on your needs.

## How to Install

### Requirements
- **Python 3.12+** (Python 3.13 supported)
- **64-bit operating system** (Windows, macOS, Linux)

### Basic Installation

```bash
# For most users - includes core forecasting functionality
pip install openstef

# Core forecasting models only
pip install openstef-models

# Backtesting and evaluation tools
pip install openstef-beam

# With all optional components
pip install "openstef[all]"
```

### Modern Package Managers

```bash
# Using uv (recommended for development)
uv add openstef

# Using conda
conda install -c conda-forge openstef
```

For detailed installation instructions including troubleshooting, see our [Installation Guide](https://openstef.github.io/openstef/v4/user_guide/installation.html).

## Examples

Explore practical examples in our [`examples/`](examples/) folder:

- **Forecasting workflows** - Complete end-to-end forecasting examples
- **Model benchmarking** - Compare different forecasting approaches
- **Feature engineering** - Time series feature creation examples
- **Evaluation and analysis** - Performance assessment workflows

Each example includes its own README with detailed explanations and usage instructions.

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

If you use OpenSTEF in your research, please cite our work:

```bibtex
@software{openstef,
  title = {OpenSTEF: Open Short-Term Energy Forecasting},
  author = {{Contributors to the OpenSTEF project}},
  url = {https://github.com/OpenSTEF/openstef},
  version = {4.0.0},
  year = {2025},
  publisher = {LF Energy}
}
```

For academic publications, you may also reference our methodology papers available on the [OpenSTEF website](https://lfenergy.org/projects/openstef/).

## Contact

- **Documentation**: [https://openstef.github.io/openstef/v4/](https://openstef.github.io/openstef/v4/)
- **Support Guide**: [https://openstef.github.io/openstef/v4/project/support.html](https://openstef.github.io/openstef/v4/project/support.html)
- **GitHub Discussions**: [https://github.com/OpenSTEF/openstef/discussions](https://github.com/OpenSTEF/openstef/discussions)
- **Issues**: [https://github.com/OpenSTEF/openstef/issues](https://github.com/OpenSTEF/openstef/issues)
- **Email**: openstef@lfenergy.org