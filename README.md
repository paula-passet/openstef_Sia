<!--
SPDX-FileCopyrightText: 2017-2025 Contributors to the OpenSTEF project <openstef@lfenergy.org>

SPDX-License-Identifier: MPL-2.0
-->

![OpenSTEF Logo](https://raw.githubusercontent.com/OpenSTEF/openstef/main/docs/source/_static/logo-light.png#gh-light-mode-only)
![OpenSTEF Logo](https://raw.githubusercontent.com/OpenSTEF/openstef/main/docs/source/_static/logo-dark.png#gh-dark-mode-only)

[![PyPI version](https://badge.fury.io/py/openstef.svg)](https://badge.fury.io/py/openstef)
[![License: MPL 2.0](https://img.shields.io/badge/License-MPL%202.0-brightgreen.svg)](https://opensource.org/licenses/MPL-2.0)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Build Status](https://github.com/OpenSTEF/openstef/workflows/Test/badge.svg)](https://github.com/OpenSTEF/openstef/actions)
[![Downloads](https://static.pepy.tech/badge/openstef)](https://pepy.tech/project/openstef)
[![CII Best Practices](https://bestpractices.coreinfrastructure.org/projects/5585/badge)](https://bestpractices.coreinfrastructure.org/projects/5585)

## What is OpenSTEF

**OpenSTEF** is a complete machine learning framework for short-term energy forecasting. It provides probabilistic forecasts for electricity grid load, renewable generation, and energy components, enabling grid operators to anticipate congestion and optimize asset utilization. OpenSTEF combines measurements with weather data and market prices to deliver forecasts through both API and graphical interfaces.

For more information, visit the [OpenSTEF website](https://www.lfenergy.org/projects/openstef/).

## Brief Monorepo Overview

This repository contains the complete OpenSTEF ecosystem organized as a monorepo with multiple specialized packages:

- **`openstef`** - Meta-package providing unified access to core components
- **`packages/openstef-core`** - Core utilities, dataset types, and shared functionality  
- **`packages/openstef-models`** - ML models, feature engineering, and forecasting workflows
- **`packages/openstef-beam`** - Backtesting, Evaluation, Analysis, and Metrics framework
- **`packages/openstef-meta`** - Meta-learning and ensemble forecasting capabilities
- **`examples/`** - Comprehensive examples and tutorials
- **`docs/`** - Complete documentation and API reference

## How to Install

### Requirements
- Python 3.12 or higher
- 64-bit operating system (Windows, macOS, Linux)

### Basic Installation

```bash
# Install the complete OpenSTEF suite
pip install openstef

# Or install specific components
pip install openstef-models  # Core forecasting models only
pip install openstef-beam    # Benchmarking and evaluation tools
```

### Development Installation

```bash
# Clone the repository
git clone https://github.com/paula-passet/openstef_Sia.git
cd openstef_Sia

# Install with uv (recommended)
uv sync --dev

# Or with pip
pip install -e .
```

### Optional Dependencies

```bash
# Install with all optional features
pip install "openstef[all]"

# Or specific feature sets
pip install "openstef[beam]"     # Benchmarking tools
pip install "openstef[meta]"     # Meta-learning capabilities
```

## Examples

Explore the [`examples/`](examples/) folder for comprehensive tutorials and use cases:

- **Benchmarking** - Compare forecasting models with the Liander 2024 benchmark
- **Feature Engineering** - Configure model pipelines and isotonic calibration
- **Ensemble Methods** - Advanced forecasting with multiple models

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

If you use OpenSTEF in your research, please cite our work. Citation information and BibTeX entries are available in our [CITATION.cff](CITATION.cff) file.

## Contact

For questions, support, or collaboration opportunities:

- Visit our [Support page](https://github.com/OpenSTEF/.github/blob/main/SUPPORT.md)
- Join discussions in [GitHub Discussions](https://github.com/OpenSTEF/openstef/discussions)
- Report issues in our [Issue Tracker](https://github.com/OpenSTEF/openstef/issues)