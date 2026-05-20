Now I have enough information to generate the README. Let me compile it based on the structure plan and all the gathered information.

<!--
SPDX-FileCopyrightText: 2017-2025 Contributors to the OpenSTEF project <openstef@lfenergy.org>

SPDX-License-Identifier: MPL-2.0
-->

<p align="center">
  <a href="https://www.lfenergy.org/projects/openstef/">
    <img src="https://raw.githubusercontent.com/OpenSTEF/.github/main/profile/logo.png" alt="OpenSTEF Logo" width="400">
  </a>
</p>

## Badges

[![Downloads](https://static.pepy.tech/badge/openstef)](https://pepy.tech/project/openstef)
[![Downloads](https://static.pepy.tech/badge/openstef/month)](https://pepy.tech/project/openstef)
[![CII Best Practices](https://bestpractices.coreinfrastructure.org/projects/5585/badge)](https://bestpractices.coreinfrastructure.org/projects/5585)
[![License: MPL-2.0](https://img.shields.io/badge/License-MPL%202.0-brightgreen.svg)](LICENSE.md)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/downloads/)
[![Release](https://img.shields.io/badge/release-v4.0.0-blue)](https://github.com/paula-passet/openstef_Sia/releases/tag/release/v4.0.0)

## What is OpenSTEF

**OpenSTEF** (Open Short-Term Energy Forecasting) is an open-source, model-agnostic Python framework that provides complete machine learning pipelines for short-term energy forecasting — including data preprocessing, feature engineering, model training, probabilistic forecasting, evaluation, and post-processing. It is designed for use cases such as congestion management, transport forecasts, grid loss prediction, and more. OpenSTEF generates probabilistic forecasts with uncertainty bandwidths, not just single-point predictions.

For more information, visit the [OpenSTEF project page on LF Energy](https://www.lfenergy.org/projects/openstef/).

## Repository Structure

OpenSTEF 4.0.0 is organized as a monorepo with specialized packages under the `packages/` directory:

| Package | Purpose |
|---------|---------|
| **openstef** | Meta-package that installs all core components |
| **openstef-core** | Core utilities, dataset types, shared types and base models |
| **openstef-models** | ML models, feature engineering, data processing |
| **openstef-beam** | Backtesting, Evaluation, Analysis, and Metrics |
| **openstef-meta** | Meta models for OpenSTEF |

Additional top-level directories include `examples/` for tutorials and `docs/` for documentation sources.

## How to Install

**Requirements:** Python ≥3.12, <4.0 on a 64-bit operating system.

```bash
# Install the full framework (all packages)
pip install openstef

# Or install individual packages
pip install openstef-models
pip install openstef-beam
pip install openstef-core

# Install with optional features
pip install "openstef-models[lgbm]"
pip install "openstef-models[xgb-cpu]"
pip install "openstef-beam[all]"
```

Using [uv](https://docs.astral.sh/uv/) (recommended for development):

```bash
uv add openstef
```

For the complete installation guide including troubleshooting, see the [Installation Documentation](https://openstef.github.io/openstef/v4/user_guide/installation.html).

## Examples

The [`examples/`](examples/) directory contains runnable tutorials demonstrating OpenSTEF's capabilities, including:

- **Forecasting Quickstart** — end-to-end forecasting pipeline
- **Feature Engineering** — domain-specific energy feature creation
- **Ensemble Forecasting** — combining multiple base forecasters
- **Benchmarking** — standardized evaluation using the Liander 2024 benchmark dataset

See the [`examples/README.md`](examples/README.md) for a full overview of available examples.

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

If you use OpenSTEF in your research, please cite the project. Refer to the [CITATION.cff](CITATION.cff) file in this repository for the preferred citation format, or use:

> OpenSTEF: Open Short-Term Energy Forecasting. Contributors to the OpenSTEF project, LF Energy, 2017–2025. https://github.com/OpenSTEF/openstef

## Contact

- **Slack:** [LF Energy Slack](https://slack.lfenergy.org/)
- **Email:** openstef@lfenergy.org
- **[Support Guide](https://openstef.github.io/openstef/v4/project/support.html)** — how to get help
- **[Issue Tracker](https://github.com/OpenSTEF/openstef/issues)** — bug reports and feature requests
- **[LF Energy Project Page](https://www.lfenergy.org/projects/openstef/)** — official project homepage