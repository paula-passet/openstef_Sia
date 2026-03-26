<!--
SPDX-FileCopyrightText: 2017-2025 Contributors to the OpenSTEF project <openstef@lfenergy.org>

SPDX-License-Identifier: MPL-2.0
-->

<img src="https://raw.githubusercontent.com/OpenSTEF/openstef/main/docs/logo_color.png" alt="OpenSTEF Logo" width="200">

<!-- Badges -->

[![Downloads](https://static.pepy.tech/badge/openstef)](https://pepy.tech/project/openstef)
[![Downloads](https://static.pepy.tech/badge/openstef/month)](https://pepy.tech/project/openstef)
[![CII Best Practices](https://bestpractices.coreinfrastructure.org/projects/5585/badge)](https://bestpractices.coreinfrastructure.org/projects/5585)
[![License: MPL 2.0](https://img.shields.io/badge/License-MPL%202.0-brightgreen.svg)](https://opensource.org/licenses/MPL-2.0)
[![Build Status](https://github.com/OpenSTEF/openstef/workflows/build/badge.svg)](https://github.com/OpenSTEF/openstef/actions)

## What is OpenSTEF

OpenSTEF is a complete framework for short-term energy forecasting that combines machine learning models, backtesting capabilities, and comprehensive evaluation tools. The framework enables energy system operators and researchers to create accurate, probabilistic forecasts for energy consumption, generation, and grid management. Learn more at the [OpenSTEF website](https://openstef.github.io/openstef/).

## Brief Monorepo Overview

OpenSTEF 4.0 is organized as a monorepo with specialized packages: **openstef-core** provides foundational data structures and utilities, **openstef-models** contains forecasting algorithms and feature engineering, **openstef-beam** offers backtesting and evaluation capabilities, and **openstef-meta** enables ensemble forecasting workflows.

## How to Install

```bash
# Install complete OpenSTEF framework
pip install openstef

# Install specific packages
pip install openstef-models  # Core forecasting models
pip install openstef-beam    # Backtesting and evaluation
pip install openstef-core    # Core utilities and data structures
pip install openstef-meta    # Ensemble forecasting

# Development installation with all features
pip install "openstef[all]"
```

**Requirements:** Python 3.12+ on 64-bit systems (Windows, macOS, Linux).

For detailed installation instructions, troubleshooting, and development setup, see our [Installation Guide](https://openstef.github.io/openstef/v4/user_guide/installation.html).

## Examples

Explore practical examples in the [`examples/`](examples/) folder, including:

- Basic forecasting workflows and model configuration
- Benchmark comparisons using the Liander 2024 dataset  
- Ensemble forecasting and isotonic calibration techniques
- Custom pipeline development and feature engineering

Each example includes detailed documentation and can be run independently. See the [examples README](examples/README.md) for a complete overview.

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

Please cite OpenSTEF in your research and publications:

```bibtex
@software{openstef,
  title = {OpenSTEF: Open Short Term Energy Forecasting},
  author = {{Contributors to the OpenSTEF project}},
  url = {https://github.com/OpenSTEF/openstef},
  version = {4.0.0},
  year = {2025},
  license = {MPL-2.0}
}
```

For specific algorithms or methods, additional citations may be found in the relevant documentation sections.

## Contact

- **Documentation & Guides:** [https://openstef.github.io/openstef/](https://openstef.github.io/openstef/)
- **Support & Questions:** See our [Support Guide](https://github.com/OpenSTEF/.github/blob/main/SUPPORT.md)
- **Bug Reports & Features:** [GitHub Issues](https://github.com/OpenSTEF/openstef/issues)
- **Community Discussions:** [GitHub Discussions](https://github.com/OpenSTEF/openstef/discussions)
- **Email:** openstef@lfenergy.org
- **LF Energy Project Page:** [https://www.lfenergy.org/projects/openstef/](https://www.lfenergy.org/projects/openstef/)