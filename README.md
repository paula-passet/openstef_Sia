# OpenSTEF

[![Downloads](https://static.pepy.tech/badge/openstef)](https://pepy.tech/project/openstef)
[![Downloads](https://static.pepy.tech/badge/openstef/month)](https://pepy.tech/project/openstef)
[![CII Best Practices](https://bestpractices.coreinfrastructure.org/projects/5585/badge)](https://bestpractices.coreinfrastructure.org/projects/5585)

## What is OpenSTEF

OpenSTEF is a modular framework for short-term energy forecasting that combines machine learning models, feature engineering, and comprehensive evaluation tools. The platform provides everything needed to build, test, and deploy probabilistic forecasting models for energy systems. Learn more at [openstef.github.io](https://openstef.github.io/openstef).

## Brief Monorepo Overview

This repository contains multiple specialized packages organized in a monorepo structure:

- **openstef-core**: Core utilities, dataset types, and shared base models
- **openstef-models**: ML models, feature engineering, and data processing workflows  
- **openstef-beam**: Backtesting, Evaluation, Analysis, and Metrics framework
- **openstef-meta**: Ensemble forecasting and meta-learning models
- **examples**: Tutorials and benchmarking examples

## How to Install

### Requirements
- Python 3.12+ (Python 3.13 supported)
- 64-bit operating system (Windows, macOS, Linux)

### Basic Installation

```bash
# For most users - includes core forecasting capabilities
pip install openstef

# Individual packages
pip install openstef-models    # Core forecasting models
pip install openstef-beam      # Evaluation and benchmarking
pip install openstef-meta      # Ensemble models

# All optional components
pip install "openstef[all]"
```

### Modern Package Managers

```bash
# Using uv (recommended for development)
uv add openstef

# Using conda
conda install -c conda-forge openstef
```

## Examples

Explore hands-on examples in the [`examples/`](examples/) directory:

- **Quick Start Examples**: Basic forecasting workflows and model configuration
- **Benchmarking Examples**: Complete evaluation studies using the Liander 2024 dataset
- **Advanced Tutorials**: Feature engineering, ensemble models, and calibration techniques

See the [examples README](examples/README.md) for a complete overview of available tutorials and benchmarks.

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

### Citation Information

If you use OpenSTEF in your research or applications, please cite:

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

For academic publications, you may also reference the LF Energy OpenSTEF project page: https://www.lfenergy.org/projects/openstef/

## Contact

- **Documentation**: [openstef.github.io](https://openstef.github.io/openstef/v4/)
- **GitHub Discussions**: [Community Q&A and discussions](https://github.com/OpenSTEF/openstef/discussions)
- **Issue Tracker**: [Bug reports and feature requests](https://github.com/OpenSTEF/openstef/issues)
- **Email**: Contact us at openstef@lfenergy.org
- **Slack**: Join the [LF Energy Slack workspace](https://slack.lfenergy.org/) (#openstef channel)

For detailed support information, see our [Support Guide](https://openstef.github.io/openstef/v4/project/support/).