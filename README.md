# OpenSTEF

[![Downloads](https://static.pepy.tech/badge/openstef)](https://pepy.tech/project/openstef)
[![Downloads](https://static.pepy.tech/badge/openstef/month)](https://pepy.tech/project/openstef)
[![CII Best Practices](https://bestpractices.coreinfrastructure.org/projects/5585/badge)](https://bestpractices.coreinfrastructure.org/projects/5585)

OpenSTEF is a complete framework for short-term energy forecasting with advanced backtesting, evaluation, and analysis capabilities. Version 4.0 introduces a modular architecture with enhanced type safety and modern Python development practices.

Visit [openstef.github.io/openstef](https://openstef.github.io/openstef) for complete documentation.

## Monorepo Structure

This repository contains multiple specialized packages:

- **openstef-core**: Core datasets, utilities, and shared types
- **openstef-models**: ML models, feature engineering, and preprocessing pipelines  
- **openstef-beam**: Backtesting, Evaluation, Analysis, and Metrics framework
- **openstef-meta**: Ensemble forecasting and advanced model combinations
- **openstef**: Meta-package combining core forecasting functionality
- **examples**: Benchmarks and usage examples

## Installation

**Requirements**: Python 3.12+ on 64-bit systems

```bash
# Complete forecasting framework
pip install openstef

# Core models only
pip install openstef-models

# With evaluation and analysis tools
pip install "openstef[beam]"

# All optional components
pip install "openstef[all]"
```

For development setup:
```bash
git clone https://github.com/OpenSTEF/openstef.git
cd openstef
uv sync --dev
```

## Examples

Explore practical examples in the [`examples/`](examples/) directory:

- **Benchmarks**: Run the Liander 2024 benchmark with XGBoost, ensemble methods, and comparison tools
- **Forecasting**: Basic model training and prediction workflows
- **Configuration**: Customize model pipelines and preprocessing steps
- **Calibration**: Apply isotonic quantile calibration to improve forecast reliability

Each example includes a detailed README with step-by-step instructions.

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

If you use OpenSTEF in your research, please cite:

```bibtex
@software{openstef_2025,
  title = {OpenSTEF: Open Short Term Energy Forecasting},
  author = {{Contributors to the OpenSTEF project}},
  url = {https://github.com/OpenSTEF/openstef},
  version = {4.0.0},
  year = {2025},
  publisher = {LF Energy Foundation},
  license = {MPL-2.0}
}
```

## Contact

- **Documentation**: [openstef.github.io/openstef](https://openstef.github.io/openstef/v4/)
- **GitHub Issues**: [github.com/OpenSTEF/openstef/issues](https://github.com/OpenSTEF/openstef/issues)
- **Discussions**: [github.com/OpenSTEF/openstef/discussions](https://github.com/OpenSTEF/openstef/discussions)
- **Email**: openstef@lfenergy.org