<!--
SPDX-FileCopyrightText: 2017-2025 Contributors to the OpenSTEF project <openstef@lfenergy.org>

SPDX-License-Identifier: MPL-2.0
-->

<p align="center">
  <a href="https://www.lfenergy.org/projects/openstef/">
    <img src="https://raw.githubusercontent.com/OpenSTEF/.github/main/profile/logo.png" alt="OpenSTEF Logo" width="400">
  </a>
</p>

<h1 align="center">OpenSTEF</h1>

<p align="center">
  <a href="https://pepy.tech/project/openstef"><img src="https://static.pepy.tech/badge/openstef" alt="Downloads"></a>
  <a href="https://pepy.tech/project/openstef"><img src="https://static.pepy.tech/badge/openstef/month" alt="Monthly Downloads"></a>
  <a href="https://bestpractices.coreinfrastructure.org/projects/5585"><img src="https://bestpractices.coreinfrastructure.org/projects/5585/badge" alt="CII Best Practices"></a>
  <a href="https://github.com/paula-passet/openstef_Sia/releases/tag/release/v4.0.0"><img src="https://img.shields.io/badge/version-4.0.0-blue" alt="Version 4.0.0"></a>
  <a href="LICENSE.md"><img src="https://img.shields.io/badge/license-MPL--2.0-brightgreen" alt="License: MPL-2.0"></a>
</p>

## What is OpenSTEF

**OpenSTEF** (Open Short-Term Energy Forecasting) is an open-source Python library that provides a complete machine learning framework for short-term energy forecasting. It delivers probabilistic forecasts with uncertainty bandwidths through pipelines for data preprocessing, feature engineering, model training, evaluation, and post-processing. OpenSTEF includes domain-specific feature engineering for the energy sector and supports use cases such as congestion management, transport forecasts, and grid loss prediction.

Learn more at the [OpenSTEF project page](https://www.lfenergy.org/projects/openstef/).

## Monorepo Overview

OpenSTEF 4.0 is structured as a modular monorepo under the `packages/` directory:

| Package | Purpose |
|---------|---------|
| **openstef** | Meta-package installing all core components |
| **openstef-core** | Shared data types, interfaces, base classes, and utilities |
| **openstef-models** | ML models, feature engineering, data preprocessing pipelines |
| **openstef-beam** | Backtesting, Evaluation, Analysis, and Metrics |
| **openstef-meta** | Meta-learning and ensemble models |

Each package can be installed and used independently, allowing you to include only the components you need.

## How to Install

**Requirements:** Python ≥3.12, 64-bit OS (Windows, macOS, Linux)

```bash
# Install the full framework (all packages)
pip install openstef

# Install only the forecasting models
pip install openstef-models

# Install with optional features
pip install "openstef-models[lgbm]"
pip install "openstef-models[xgb-cpu]"
```

Using [uv](https://github.com/astral-sh/uv) (recommended for development):

```bash
uv add openstef
```

For detailed instructions including GPU support and development setup, see the [Installation Guide](https://openstef.github.io/openstef/v4/user_guide/installation.html).

## Examples

Explore ready-to-run examples in the [`examples/`](examples/) folder. The folder contains its own `README.md` with an overview of available examples and instructions for getting started.

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

If you use OpenSTEF in your research, please cite the project:

```bibtex
@software{openstef,
  title = {OpenSTEF: Open Short-Term Energy Forecasting},
  author = {Contributors to the OpenSTEF project},
  url = {https://github.com/OpenSTEF/openstef},
  license = {MPL-2.0},
  year = {2025}
}
```

## Contact

- **Slack:** [LF Energy Slack](https://slack.lfenergy.org/)
- **Email:** openstef@lfenergy.org
- **Issues:** [GitHub Issue Tracker](https://github.com/OpenSTEF/openstef/issues)
- **Support:** [Support Guide](https://openstef.github.io/openstef/v4/project/support.html)
- **LF Energy:** [OpenSTEF Project Page](https://www.lfenergy.org/projects/openstef/)