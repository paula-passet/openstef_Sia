<!--
SPDX-FileCopyrightText: 2017-2025 Contributors to the OpenSTEF project <openstef@lfenergy.org>

SPDX-License-Identifier: MPL-2.0
-->

<p align="center">
  <img src="https://raw.githubusercontent.com/OpenSTEF/openstef/main/docs/logos/openstef-horizontal-color.svg" alt="OpenSTEF logo" width="400"/>
</p>

<p align="center">
  <a href="https://pepy.tech/project/openstef"><img src="https://static.pepy.tech/badge/openstef" alt="Downloads"/></a>
  <a href="https://pepy.tech/project/openstef"><img src="https://static.pepy.tech/badge/openstef/month" alt="Downloads per month"/></a>
  <a href="https://bestpractices.coreinfrastructure.org/projects/5585"><img src="https://bestpractices.coreinfrastructure.org/projects/5585/badge" alt="CII Best Practices"/></a>
  <a href="https://github.com/paula-passet/openstef_Sia/releases/tag/release/v4.0.0"><img src="https://img.shields.io/badge/release-v4.0.0-blue" alt="Release v4.0.0"/></a>
  <a href="LICENSE.md"><img src="https://img.shields.io/badge/license-MPL--2.0-green" alt="License: MPL-2.0"/></a>
</p>

---

## What is OpenSTEF?

**OpenSTEF** (Open Short-Term Energy Forecasting) is an open-source Python framework for generating accurate short-term energy load forecasts hours to days ahead. It provides complete, model-agnostic pipelines covering data preprocessing, feature engineering, model training, probabilistic forecasting, evaluation, and post-processing. OpenSTEF includes built-in domain knowledge for the energy sector — such as solar radiation to PV generation estimates — and supports use cases including congestion management, transport forecasts, and grid loss prediction. Learn more at the [LF Energy OpenSTEF project page](https://www.lfenergy.org/projects/openstef/).

---

## Repository Structure

OpenSTEF 4.0 is organised as a **modular monorepo**. Each package is self-contained and can be installed independently:

| Package | Purpose |
|---|---|
| **openstef** | Meta-package — installs the full framework |
| **openstef-core** | Core data types, interfaces, shared utilities, and base classes |
| **openstef-models** | Forecasting models, feature engineering, and data preprocessing pipelines |
| **openstef-beam** | Backtesting, Evaluation, Analysis, and Metrics (BEAM) |
| **openstef-meta** | Meta-learning and modern ensemble model architectures |

---

## How to Install

**Requirements:** Python ≥ 3.12, 64-bit OS (Windows, macOS, Linux)

```bash
# Install the complete framework
pip install openstef

# Or install only the packages you need
pip install openstef-models
pip install openstef-beam
pip install openstef-core

# Install with optional model backends
pip install "openstef-models[lgbm]"
pip install "openstef-models[xgb-cpu]"

# Using uv (recommended for development)
uv add openstef
```

See the [Installation Guide](https://openstef.github.io/openstef/v4/user_guide/installation.html) for full details, including optional extras and development setup.

---

## Examples

Ready-to-run examples are available in the [`examples/`](examples/) folder. Refer to the [`examples/README.md`](examples/README.md) for an overview of available examples and setup instructions.

Before running any example, install all dependencies with:

```bash
uv sync --all-extras --all-groups --all-packages
```

---

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

If you use OpenSTEF in your research, please cite it using the metadata in [`CITATION.cff`](CITATION.cff). Most reference managers and GitHub's **Cite this repository** button can generate a citation automatically from this file.

---

## Contact

- **Slack:** [LF Energy Slack](https://slack.lfenergy.org/) — `#openstef` channel
- **Email:** [openstef@lfenergy.org](mailto:openstef@lfenergy.org)
- **Community meetings:** [OpenSTEF four-weekly community meeting](https://lf-energy.atlassian.net/wiki/spaces/OS/pages/32278358/OpenSTEF+four-weekly+community+meeting)
- **Issue tracker:** [GitHub Issues](https://github.com/OpenSTEF/openstef/issues)