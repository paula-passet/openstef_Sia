# OpenSTEF

<p align="center">
  <img src="https://raw.githubusercontent.com/OpenSTEF/openstef/main/docs/logo_color.png" alt="OpenSTEF Logo" width="200"/>
</p>

[![Downloads](https://static.pepy.tech/badge/openstef)](https://pepy.tech/project/openstef)
[![Downloads](https://static.pepy.tech/badge/openstef/month)](https://pepy.tech/project/openstef)
[![CII Best Practices](https://bestpractices.coreinfrastructure.org/projects/5585/badge)](https://bestpractices.coreinfrastructure.org/projects/5585)

## What is OpenSTEF

OpenSTEF is a modular library for creating short-term forecasts in the energy sector. OpenSTEF 4.0 introduces enhanced modularity, type safety, and modern Python development practices with specialized packages for different forecasting needs. Visit the [OpenSTEF website](https://lfenergy.org/projects/openstef/) for comprehensive project information.

## Brief Monorepo Overview

OpenSTEF 4.0 uses a monorepo structure with specialized packages:
- **openstef-core**: Core utilities, datasets, and shared types
- **openstef-models**: ML models and feature engineering
- **openstef-beam**: Backtesting, Evaluation, Analysis, and Metrics
- **openstef-meta**: Ensemble forecasting and meta-models

## How to Install

Install OpenSTEF using pip or modern package managers:

```bash
# Complete OpenSTEF suite
pip install openstef

# Core forecasting functionality
pip install openstef-models

# Backtesting and evaluation tools
pip install openstef-beam

# Using uv (recommended for development)
uv add openstef
```

**Requirements**: Python 3.12+ on 64-bit systems (Windows, macOS, Linux)

## Examples

Explore practical examples in the [`examples/`](examples/) folder. The examples include:

- **Basic forecasting**: Quick start with XGBoost and linear models
- **Benchmarking**: Comparing multiple models on the Liander 2024 dataset
- **Feature engineering**: Time-domain and weather-domain transformations
- **Ensemble models**: Combining multiple forecasters for improved accuracy
- **Isotonic calibration**: Calibrating probabilistic forecasts

See the [examples README](examples/README.md) for a complete overview and setup instructions.

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

When using OpenSTEF in academic work, please cite:

```bibtex
@software{openstef_2025,
  title = {{OpenSTEF}: Open Short Term Energy Forecasting},
  author = {{Contributors to the OpenSTEF project}},
  year = {2025},
  url = {https://github.com/OpenSTEF/openstef},
  version = {4.0.0}
}
```

## Contact

- **Documentation**: [OpenSTEF Documentation](https://openstef.github.io/openstef/)
- **Support**: [GitHub Discussions](https://github.com/OpenSTEF/openstef/discussions)
- **Issues**: [GitHub Issues](https://github.com/OpenSTEF/openstef/issues)
- **Email**: [openstef@lfenergy.org](mailto:openstef@lfenergy.org)