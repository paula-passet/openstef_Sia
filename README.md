# OpenSTEF

![OpenSTEF Logo](https://raw.githubusercontent.com/OpenSTEF/openstef/main/docs/logo/openstef-logo-color.png)

[![Downloads](https://static.pepy.tech/badge/openstef)](https://pepy.tech/project/openstef)
[![Downloads](https://static.pepy.tech/badge/openstef/month)](https://pepy.tech/project/openstef)
[![CII Best Practices](https://bestpractices.coreinfrastructure.org/projects/5585/badge)](https://bestpractices.coreinfrastructure.org/projects/5585)
[![License: MPL 2.0](https://img.shields.io/badge/License-MPL_2.0-brightgreen.svg)](https://opensource.org/licenses/MPL-2.0)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)

OpenSTEF is a modular library for creating short-term energy forecasts. Version 4.0 introduces a complete architectural refactor with enhanced modularity, comprehensive backtesting and evaluation capabilities, and modern Python development practices.

Visit the [OpenSTEF website](https://openstef.github.io/openstef/v4/) for comprehensive documentation and guides.

## Brief Monorepo Overview

OpenSTEF 4.0 uses a modular monorepo structure with specialized packages. The main packages include `openstef-core` for foundational data structures, `openstef-models` for machine learning models and preprocessing, `openstef-beam` for backtesting and evaluation, and `openstef-meta` for ensemble forecasting capabilities.

## How to Install

### Basic Installation

```bash
# Install OpenSTEF with core forecasting models
pip install openstef

# Install with all optional components
pip install "openstef[all]"

# Individual packages
pip install openstef-models  # Core forecasting models
pip install openstef-beam    # Backtesting and evaluation
pip install openstef-meta    # Ensemble forecasting
```

### Modern Package Managers

```bash
# Using uv (recommended for development)
uv add openstef

# Using conda
conda install -c conda-forge openstef
```

**Requirements:** Python 3.12+ and 64-bit operating system (Windows, macOS, Linux).

For detailed installation instructions including troubleshooting, see the [Installation Guide](https://openstef.github.io/openstef/v4/user_guide/installation.html).

## Examples

Explore practical examples in the [`examples/`](examples/) folder, including:

- **Quick Start Tutorial** - Basic forecasting workflow
- **Benchmark Comparisons** - Model performance evaluation
- **Feature Engineering** - Custom preprocessing pipelines
- **Ensemble Forecasting** - Multi-model approaches

See the [examples README](examples/README.md) for a complete overview of available tutorials and use cases.

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

If you use OpenSTEF in academic research, please cite our work:

```bibtex
@software{openstef,
  title = {OpenSTEF: Open Short Term Energy Forecasting},
  author = {{Contributors to the OpenSTEF project}},
  url = {https://github.com/OpenSTEF/openstef},
  version = {4.0.0},
  year = {2025},
  publisher = {LF Energy Foundation},
  license = {MPL-2.0}
}
```

For additional citation formats and research papers, see our [Citations Guide](https://openstef.github.io/openstef/v4/project/citations.html).

## Contact

- **Support Guide**: [Getting Help Documentation](https://openstef.github.io/openstef/v4/project/support.html)
- **GitHub Discussions**: [Community Q&A](https://github.com/OpenSTEF/openstef/discussions)
- **Issues**: [Bug Reports & Feature Requests](https://github.com/OpenSTEF/openstef/issues)
- **Email**: openstef@lfenergy.org
- **Project Homepage**: [LF Energy OpenSTEF](https://www.lfenergy.org/projects/openstef/)