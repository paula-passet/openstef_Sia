<!-- 
SPDX-FileCopyrightText: 2017-2025 Contributors to the OpenSTEF project <openstef@lfenergy.org>
SPDX-License-Identifier: MPL-2.0
-->

# OpenSTEF

[![Downloads](https://static.pepy.tech/badge/openstef)](https://pepy.tech/project/openstef)
[![Downloads](https://static.pepy.tech/badge/openstef/month)](https://pepy.tech/project/openstef)
[![CII Best Practices](https://bestpractices.coreinfrastructure.org/projects/5585/badge)](https://bestpractices.coreinfrastructure.org/projects/5585)
[![License: MPL 2.0](https://img.shields.io/badge/License-MPL_2.0-brightgreen.svg)](https://opensource.org/licenses/MPL-2.0)

## What is OpenSTEF

OpenSTEF is a machine learning pipeline for short-term energy forecasting. It provides probabilistic forecasts with confidence intervals for electricity consumption and renewable generation. The library includes data validation, feature engineering, model training, and uncertainty quantification in a complete production-ready system.

Visit [openstef.lfenergy.org](https://www.lfenergy.org/projects/openstef/) to learn more about the project and its applications in the energy sector.

## Brief Monorepo Overview

This repository contains the complete OpenSTEF v4.0 ecosystem as a monorepo with modular packages:
- `openstef` - Meta-package with core forecasting components
- `openstef-core` - Core utilities, datasets, and shared types  
- `openstef-models` - ML models and feature engineering
- `openstef-beam` - Backtesting, evaluation, analysis and metrics
- `openstef-meta` - Ensemble forecasting and meta-learning
- `docs` - Documentation and examples

## How to Install

**Requirements**: Python 3.12+ on 64-bit systems (Windows, macOS, Linux)

### Basic Installation
```bash
# Install the main package
pip install openstef

# Or install specific components
pip install openstef-models  # Core forecasting models
pip install openstef-beam    # Evaluation and benchmarking
```

### Development Installation
```bash
# Clone and set up for development
git clone https://github.com/paula-passet/openstef_Sia.git
cd openstef_Sia
uv sync --dev

# Run tests and quality checks
uv run poe all
```

### Modern Package Managers
```bash
# Using uv (recommended)
uv add openstef

# Using conda
conda install -c conda-forge openstef
```

For detailed installation instructions including troubleshooting, see the [Installation Guide](https://openstef.github.io/openstef/index.html).

## Examples

Explore practical examples in the [`examples/`](examples/) directory:
- **Benchmarks**: Compare forecasting models on real datasets
- **Tutorials**: Step-by-step guides for common use cases
- **Workflows**: Complete forecasting pipeline examples

See the [examples README](examples/README.md) for a complete overview of available examples and getting started instructions.

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
@software{openstef2025,
  title = {OpenSTEF: Open Short Term Energy Forecasting},
  author = {{OpenSTEF Contributors}},
  year = {2025},
  url = {https://github.com/OpenSTEF/openstef},
  version = {4.0.0}
}
```

For the latest citation information, see our [Citation Guidelines](https://openstef.github.io/openstef/index.html).

## Contact

For questions, support, and community discussions, visit our [Support Page](https://github.com/OpenSTEF/.github/blob/main/SUPPORT.md) which includes:

- Community forums and discussion channels
- Issue reporting guidelines
- Professional support options
- Developer communication channels