<!--
SPDX-FileCopyrightText: 2017-2025 Contributors to the OpenSTEF project <openstef@lfenergy.org>

SPDX-License-Identifier: MPL-2.0
-->

# OpenSTEF

<!-- Badges -->

[![Downloads](https://static.pepy.tech/badge/openstef)](https://pepy.tech/project/openstef)
[![Downloads](https://static.pepy.tech/badge/openstef/month)](https://pepy.tech/project/openstef)
[![CII Best Practices](https://bestpractices.coreinfrastructure.org/projects/5585/badge)](https://bestpractices.coreinfrastructure.org/projects/5585)
[![Release](https://img.shields.io/github/v/release/paula-passet/openstef_Sia?include_prereleases&label=release%2Fv4.0.0)](https://github.com/paula-passet/openstef_Sia/releases/tag/release/v4.0.0)

## What is OpenSTEF

OpenSTEF is a comprehensive Python framework for short-term energy forecasting, providing modular components for machine learning-based predictions in the energy sector. The library offers complete workflows from data preprocessing to model evaluation, supporting both single forecasters and ensemble methods. For more information, visit the [OpenSTEF website](https://lfenergy.org/projects/openstef/).

## Brief Monorepo Overview

This repository contains a monorepo structure with specialized packages:

- **`openstef`** - Meta-package that orchestrates core forecasting workflows
- **`openstef-core`** - Foundation types, datasets, and utilities
- **`openstef-models`** - Machine learning models, transforms, and forecasting workflows  
- **`openstef-beam`** - Backtesting, Evaluation, Analysis, and Metrics framework
- **`openstef-meta`** - Ensemble forecasting models and combiners

Each package can be installed independently based on your specific needs.

## How to Install

### Requirements
- **Python 3.12+** (Python 3.13 supported)  
- **64-bit operating system** (Windows, macOS, Linux)

### Basic Installation

```bash
# Install the complete OpenSTEF suite
pip install openstef

# Install specific packages as needed
pip install openstef-models  # Core forecasting models
pip install openstef-beam    # Benchmarking and evaluation
pip install openstef-core    # Foundation utilities
pip install openstef-meta    # Ensemble methods

# Install with all optional dependencies
pip install "openstef[all]"
```

### Using Modern Package Managers

```bash
# Using uv (recommended for development)
uv add openstef

# Using conda
conda install -c conda-forge openstef
```

For detailed installation instructions including troubleshooting, see the [Installation Guide](https://openstef.github.io/openstef/v4/user_guide/installation.html).

## Examples

Explore practical examples in the [`examples/`](examples/) folder, including:

- **Benchmark Studies**: Compare forecasting models on standardized datasets
- **Forecasting Workflows**: End-to-end examples for different use cases
- **Model Configuration**: How to set up and customize forecasting pipelines

The examples folder contains its own README with an overview of available tutorials and use cases.

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
  title={OpenSTEF: Open Short Term Energy Forecasting},
  author={{OpenSTEF Contributors}},
  url={https://github.com/OpenSTEF/openstef},
  version={4.0.0},
  year={2025}
}
```

For more citation formats and academic references, see our [Citation Guide](https://openstef.github.io/openstef/v4/project/citations.html).

## Contact

For support and questions:

- **[Support Guide](https://github.com/OpenSTEF/.github/blob/main/SUPPORT.md)** - how to get help
- **[GitHub Discussions](https://github.com/OpenSTEF/openstef/discussions)** - community Q&A
- **Email**: `openstef@lfenergy.org`
- **Slack**: Join the [LF Energy Slack workspace](https://slack.lfenergy.org/) (#openstef channel)