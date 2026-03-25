<!--
SPDX-FileCopyrightText: 2017-2025 Contributors to the OpenSTEF project <openstef@lfenergy.org>

SPDX-License-Identifier: MPL-2.0
-->

![OpenSTEF Logo](https://github.com/OpenSTEF/openstef/blob/main/docs/logo_openstef.svg)

[![Downloads](https://static.pepy.tech/badge/openstef)](https://pepy.tech/project/openstef)
[![Downloads](https://static.pepy.tech/badge/openstef/month)](https://pepy.tech/project/openstef)
[![CII Best Practices](https://bestpractices.coreinfrastructure.org/projects/5585/badge)](https://bestpractices.coreinfrastructure.org/projects/5585)

## What is OpenSTEF

OpenSTEF is a complete framework for building short-term energy forecasting systems with advanced analytics capabilities. It provides probabilistic forecasting models, comprehensive backtesting, and systematic evaluation tools for the energy sector. OpenSTEF 4.0 introduces a fully modular architecture with enhanced type safety and modern development practices.

Learn more at the [OpenSTEF website](https://www.lfenergy.org/projects/openstef/).

## Brief Monorepo Overview

OpenSTEF 4.0 uses a monorepo structure with specialized packages:

- **openstef-core**: Core utilities, dataset types, and shared base models
- **openstef-models**: ML models, feature engineering, and data processing pipelines
- **openstef-beam**: Backtesting, Evaluation, Analysis, and Metrics framework
- **openstef-meta**: Ensemble forecasting and meta-learning capabilities
- **openstef**: Meta-package combining core components

Each package can be installed independently based on your specific needs.

## How to Install

### Basic Installation

```bash
# Complete framework
pip install openstef

# Core forecasting only
pip install openstef-models

# With all optional tools
pip install "openstef[all]"

# Individual components
pip install openstef-beam  # Backtesting and evaluation
pip install openstef-meta  # Ensemble models
```

### Requirements

- Python 3.12+ (Python 3.13 supported)
- 64-bit operating system (Windows, macOS, Linux)

### Modern Package Managers

```bash
# Using uv (recommended for development)
uv add openstef

# Using conda
conda install -c conda-forge openstef
```

## Examples

Explore the [examples/](examples/) directory for hands-on tutorials and use cases. The examples folder contains its own README with an overview of available examples including:

- Configuring forecasting pipelines
- Running benchmark comparisons
- Creating ensemble models
- Isotonic quantile calibration

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

If you use OpenSTEF in your research, please cite it. You can use the citation information from our [CITATION.cff](CITATION.cff) file or generate a BibTeX entry:

```bibtex
@software{openstef,
  author = {{Contributors to the OpenSTEF project}},
  title = {OpenSTEF: Open Short Term Energy Forecasting},
  url = {https://github.com/OpenSTEF/openstef},
  version = {4.0.0},
  year = {2025}
}
```

## Contact

For support and questions, please visit our [Support Page](.github/SUPPORT.md) or:

- Join discussions on [GitHub Discussions](https://github.com/OpenSTEF/openstef/discussions)
- Report issues on [GitHub Issues](https://github.com/OpenSTEF/openstef/issues)
- Contact us at `openstef@lfenergy.org`