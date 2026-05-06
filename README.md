<!--
SPDX-FileCopyrightText: 2017-2025 Contributors to the OpenSTEF project <openstef@lfenergy.org>

SPDX-License-Identifier: MPL-2.0
-->

<p align="center">
  <img src="https://raw.githubusercontent.com/OpenSTEF/.github/main/profile/assets/openstef_logo.png" alt="OpenSTEF logo" width="300"/>
</p>

<p align="center">
  <a href="https://pepy.tech/project/openstef"><img src="https://static.pepy.tech/badge/openstef" alt="Downloads"/></a>
  <a href="https://pepy.tech/project/openstef"><img src="https://static.pepy.tech/badge/openstef/month" alt="Downloads per month"/></a>
  <a href="https://bestpractices.coreinfrastructure.org/projects/5585"><img src="https://bestpractices.coreinfrastructure.org/projects/5585/badge" alt="CII Best Practices"/></a>
  <a href="https://github.com/paula-passet/openstef_Sia/releases/tag/v4.0.0"><img src="https://img.shields.io/badge/release-v4.0.0-blue" alt="Release v4.0.0"/></a>
  <a href="LICENSE.md"><img src="https://img.shields.io/badge/license-MPL--2.0-green" alt="License: MPL-2.0"/></a>
</p>

# OpenSTEF

## What is OpenSTEF?

**OpenSTEF** (Open Short-Term Energy Forecasting) is an open-source, model-agnostic Python framework for producing accurate short-term load forecasts in the energy sector — predicting load hours to days ahead. It provides complete, production-ready pipelines covering data preprocessing, feature engineering, model training, probabilistic forecasting, evaluation, and post-processing. Built-in energy-domain knowledge (such as deriving PV generation estimates from solar radiation and temperature) means it works out of the box for congestion management, transport forecasting, EV charging capacity estimation, and grid loss prediction. For more information, visit the [LF Energy OpenSTEF project page](https://www.lfenergy.org/projects/openstef/).

## Repository Structure

OpenSTEF v4.0.0 is organised as a **modular monorepo**. Each sub-package is self-contained and can be installed independently:

| Package | Purpose |
|---|---|
| `openstef-core` | Data types, interfaces, base classes, and shared testing utilities |
| `openstef-models` | Forecasting models, preprocessing pipelines, energy-specific transforms, and presets |
| `openstef-beam` | Backtesting, Evaluation, Analysis, and Metrics |
| `openstef` | Meta-package that bundles the core components |

The root of the repository also contains a `packages/` directory holding each sub-package, shared tooling configuration (`pyproject.toml`, `ruff.toml`), and CI/CD workflows under `.github/`.

## How to Install

**Requirements:** Python 3.12 or later · 64-bit operating system (Windows, macOS, Linux)

```bash
# Install the full meta-package (recommended for most users)
pip install openstef

# Install individual components only
pip install openstef-models
pip install openstef-beam
pip install openstef-core

# Using uv (recommended for development)
uv add openstef
```

For a complete installation guide including troubleshooting and development setup, see the [Installation documentation](https://openstef.github.io/openstef/v4/user_guide/installation.html).

## Examples

Runnable examples and notebooks are available in the [`examples/`](examples/) folder. See the [examples README](examples/README.md) for an overview of what is available and how to run each example.

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

If you use OpenSTEF in your research, please cite the project. A BibTeX entry and DOI reference are available on the [OpenSTEF citation page](https://openstef.github.io/openstef/v4/project/citation.html).

## Contact

- **Slack:** [LF Energy Slack](https://slack.lfenergy.org/) — join the `#openstef` channel
- **Email:** [openstef@lfenergy.org](mailto:openstef@lfenergy.org)
- **Community meetings:** [Four-weekly open meeting](https://lf-energy.atlassian.net/wiki/spaces/OS/pages/32278358/OpenSTEF+four-weekly+community+meeting)
- **Issue tracker:** [github.com/OpenSTEF/openstef/issues](https://github.com/OpenSTEF/openstef/issues)
- **Support guide:** [openstef.github.io/openstef/v4/project/support.html](https://openstef.github.io/openstef/v4/project/support.html)