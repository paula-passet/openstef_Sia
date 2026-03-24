<!--
SPDX-FileCopyrightText: 2017-2025 Contributors to the OpenSTEF project <openstef@lfenergy.org>

SPDX-License-Identifier: MPL-2.0
-->

<p align="center">
  <img src="https://avatars.githubusercontent.com/u/87270919?s=200&v=4" alt="OpenSTEF Logo" width="200"/>
</p>

# OpenSTEF

[![Downloads](https://static.pepy.tech/badge/openstef)](https://pepy.tech/project/openstef)
[![Downloads](https://static.pepy.tech/badge/openstef/month)](https://pepy.tech/project/openstef)
[![CII Best Practices](https://bestpractices.coreinfrastructure.org/projects/5585/badge)](https://bestpractices.coreinfrastructure.org/projects/5585)

## What is OpenSTEF

OpenSTEF is a modular framework for short-term energy forecasting featuring backtesting, evaluation, analysis, and metrics for probabilistic forecasting models. Version 4.0 introduces a complete architectural refactor with enhanced modularity, type safety, and modern Python development practices.

Visit the [OpenSTEF website](https://lfenergy.org/projects/openstef/) for more information.

## Brief Monorepo Overview

OpenSTEF 4.0 uses a modular architecture with specialized packages:

- **openstef-core**: Core data structures, types, and utilities
- **openstef-models**: ML models, feature engineering, and forecasting workflows  
- **openstef-meta**: Ensemble forecasting and model combination
- **openstef-beam**: Backtesting, evaluation, analysis, and metrics framework

The main `openstef` package provides convenient access to the most commonly used components.

## How to Install

**Requirements:**
- Python 3.12+ (Python 3.13 supported)
- 64-bit operating system (Windows, macOS, Linux)

**Basic Installation:**

```bash
# For most users - includes core models and utilities
pip install openstef

# Individual packages
pip install openstef-models  # Core forecasting models
pip install openstef-beam    # Backtesting and evaluation
pip install openstef-core    # Core utilities only

# All optional components
pip install "openstef[all]"
```

**Using modern package managers:**

```bash
# Using uv (recommended for development)
uv add openstef

# Using conda
conda install -c conda-forge openstef
```

## Examples

Explore hands-on tutorials and examples in the [`examples/`](examples/) folder. The examples include:

- **Basic Forecasting**: Get started with simple forecasting workflows
- **Benchmarking**: Compare different models using the Liander 2024 benchmark dataset
- **Configuration**: Learn how to configure model pipelines and presets
- **Advanced Topics**: Isotonic calibration, ensemble methods, and custom workflows

Each example folder contains its own `README.md` with detailed instructions and explanations.

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

If you use OpenSTEF in academic research, please cite it as:

**BibTeX:**
```bibtex
@software{openstef,
  title = {OpenSTEF: Open Short Term Energy Forecasting},
  author = {{Contributors to the OpenSTEF project}},
  url = {https://github.com/OpenSTEF/openstef},
  version = {4.0.0},
  year = {2025},
  doi = {10.5281/zenodo.5574962}
}
```

**APA:**
Contributors to the OpenSTEF project. (2025). OpenSTEF: Open Short Term Energy Forecasting (Version 4.0.0) [Computer software]. https://github.com/OpenSTEF/openstef

## Contact

- **Documentation**: [https://openstef.github.io/openstef/v4/](https://openstef.github.io/openstef/v4/)
- **Support Guide**: [https://openstef.github.io/openstef/v4/project/support.html](https://openstef.github.io/openstef/v4/project/support.html)
- **GitHub Discussions**: [https://github.com/OpenSTEF/openstef/discussions](https://github.com/OpenSTEF/openstef/discussions)
- **Issue Tracker**: [https://github.com/OpenSTEF/openstef/issues](https://github.com/OpenSTEF/openstef/issues)
- **Email**: openstef@lfenergy.org