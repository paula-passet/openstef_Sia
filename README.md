# OpenSTEF

[![Downloads](https://static.pepy.tech/badge/openstef)](https://pepy.tech/project/openstef)
[![Downloads](https://static.pepy.tech/badge/openstef/month)](https://pepy.tech/project/openstef)
[![CII Best Practices](https://bestpractices.coreinfrastructure.org/projects/5585/badge)](https://bestpractices.coreinfrastructure.org/projects/5585)

**OpenSTEF** is a modular framework for short-term energy forecasting that provides machine learning models, evaluation tools, and analysis capabilities. The platform offers comprehensive backtesting, evaluation, analysis, and metrics (BEAM) for forecasting performance assessment.

## Repository Structure

OpenSTEF is structured as a monorepo with specialized packages:

- **openstef-core**: Core data structures, datasets, types, and utilities
- **openstef-models**: ML models, feature engineering, and forecasting workflows  
- **openstef-beam**: Backtesting, evaluation, analysis, and metrics framework
- **openstef-meta**: Ensemble forecasting and meta-modeling capabilities
- **examples**: Benchmarks and usage examples

## Installation

**Requirements**: Python 3.12+ on 64-bit systems

```bash
# Install complete framework
pip install openstef

# Install specific components
pip install openstef-models    # Core forecasting models
pip install openstef-beam      # Evaluation and benchmarking
pip install openstef-core      # Data structures only

# With all optional dependencies
pip install "openstef[all]"
```

For development setup with uv:
```bash
git clone https://github.com/paula-passet/openstef_Sia.git
cd openstef_Sia
uv sync --dev
uv run poe all
```

## Examples

Explore the [`examples/`](examples/) directory for:

- **Benchmarks**: Liander 2024 dataset examples with XGBoost, ensemble methods
- **Configuration**: Model pipeline setup and forecasting presets
- **Calibration**: Isotonic quantile calibration for uncertainty estimation

Each example includes detailed documentation and can be run independently.

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

To cite OpenSTEF in academic work:

```bibtex
@software{openstef,
  title = {OpenSTEF: Open Short Term Energy Forecasting},
  author = {{Contributors to the OpenSTEF project}},
  url = {https://github.com/OpenSTEF/openstef},
  version = {4.0.0},
  year = {2025}
}
```

For specific components, see individual package documentation for detailed citations.

## Contact

- **Documentation**: [https://openstef.github.io/openstef/](https://openstef.github.io/openstef/)
- **Issues**: [GitHub Issues](https://github.com/OpenSTEF/openstef/issues)
- **Discussions**: [GitHub Discussions](https://github.com/OpenSTEF/openstef/discussions)
- **Email**: openstef@lfenergy.org
- **Project Home**: [LF Energy OpenSTEF](https://www.lfenergy.org/projects/openstef/)