# OpenSTEF

![OpenSTEF Logo](https://github.com/OpenSTEF/openstef/raw/main/docs/source/_static/logo-openstef.png)

[![Downloads](https://static.pepy.tech/badge/openstef)](https://pepy.tech/project/openstef)
[![Downloads](https://static.pepy.tech/badge/openstef/month)](https://pepy.tech/project/openstef)
[![CII Best Practices](https://bestpractices.coreinfrastructure.org/projects/5585/badge)](https://bestpractices.coreinfrastructure.org/projects/5585)
[![License: MPL 2.0](https://img.shields.io/badge/License-MPL_2.0-brightgreen.svg)](https://opensource.org/licenses/MPL-2.0)
[![Version](https://img.shields.io/pypi/v/openstef)](https://pypi.org/project/openstef/)

## What is OpenSTEF

OpenSTEF is a modular Python framework for short-term energy forecasting that provides machine learning models, backtesting tools, and evaluation metrics. It enables energy professionals to build, test, and deploy probabilistic forecasting solutions with modern development practices and comprehensive model validation. Learn more at the [OpenSTEF website](https://lfenergy.org/projects/openstef/).

## Brief Monorepo Overview

OpenSTEF 4.0 uses a monorepo structure with specialized packages: **openstef-core** provides core data types and utilities, **openstef-models** contains ML models and feature engineering, **openstef-beam** offers backtesting and evaluation tools, and **openstef-meta** supports ensemble forecasting. The main **openstef** package combines these components for easy installation.

## How to Install

```bash
# For most users - includes core forecasting functionality
pip install openstef

# Core forecasting models only
pip install openstef-models

# Backtesting and evaluation tools
pip install "openstef[beam]"

# Complete toolkit with all components
pip install "openstef[all]"

# Using modern package managers
uv add openstef
conda install -c conda-forge openstef
```

**Requirements:** Python 3.12+ on 64-bit systems (Windows, macOS, Linux).

## Examples

Explore comprehensive examples in the [`examples/`](examples/) folder, which contains its own README with tutorials covering forecasting workflows, model comparison benchmarks, and evaluation techniques. Start with the forecasting preset example to see OpenSTEF in action.

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

If you use OpenSTEF in your research or projects, please cite it as:

```bibtex
@software{openstef,
  author = {{Contributors to the OpenSTEF project}},
  title = {OpenSTEF: Open Short Term Energy Forecasting},
  url = {https://github.com/OpenSTEF/openstef},
  version = {4.0.0},
  year = {2025}
}
```

You can also cite specific releases using the DOI provided on our [GitHub releases page](https://github.com/OpenSTEF/openstef/releases).

## Contact

For questions, support, or collaboration:

- **Community Support**: [GitHub Discussions](https://github.com/OpenSTEF/openstef/discussions)
- **Bug Reports**: [GitHub Issues](https://github.com/OpenSTEF/openstef/issues)
- **Direct Contact**: [Support Guidelines](https://github.com/OpenSTEF/openstef/blob/main/.github/SUPPORT.md)
- **Project Homepage**: [LF Energy OpenSTEF](https://lfenergy.org/projects/openstef/)