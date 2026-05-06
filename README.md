<!--
SPDX-FileCopyrightText: 2017-2025 Contributors to the OpenSTEF project <openstef@lfenergy.org>

SPDX-License-Identifier: MPL-2.0
-->

<p align="center">
  <img src="https://raw.githubusercontent.com/OpenSTEF/.github/main/profile/assets/openstef-horizontal-color.svg" alt="OpenSTEF logo" width="400"/>
</p>

<p align="center">
  <a href="https://pepy.tech/project/openstef"><img src="https://static.pepy.tech/badge/openstef" alt="Total Downloads"/></a>
  <a href="https://pepy.tech/project/openstef"><img src="https://static.pepy.tech/badge/openstef/month" alt="Monthly Downloads"/></a>
  <a href="https://bestpractices.coreinfrastructure.org/projects/5585"><img src="https://bestpractices.coreinfrastructure.org/projects/5585/badge" alt="CII Best Practices"/></a>
  <a href="https://github.com/paula-passet/openstef_Sia/releases/tag/release/v4.0.0"><img src="https://img.shields.io/badge/release-v4.0.0-blue" alt="Release v4.0.0"/></a>
  <a href="LICENSE.md"><img src="https://img.shields.io/badge/license-MPL--2.0-brightgreen" alt="License: MPL-2.0"/></a>
</p>

---

## What is OpenSTEF?

**OpenSTEF** (Open Short-Term Energy Forecasting) is an open-source, model-agnostic Python framework for producing accurate short-term energy load forecasts hours to days ahead. It provides complete machine learning pipelines covering data preprocessing, feature engineering, model training, probabilistic forecasting, evaluation, and post-processing. Built-in domain knowledge — such as solar radiation to PV generation estimates — makes it immediately applicable to congestion management, transport forecasts, EV charging capacity, and grid loss prediction. For more information, visit the [LF Energy OpenSTEF project page](https://www.lfenergy.org/projects/openstef/).

---

## Repository Structure

OpenSTEF 4.0 is organised as a **modular monorepo**. Each package is self-contained and can be installed independently:

| Package | Purpose |
|---|---|
| **openstef** | Meta-package — installs the full framework |
| **openstef-core** | Data types, interfaces, base classes, and shared utilities |
| **openstef-models** | Forecasting models, feature engineering, and data preprocessing pipelines |
| **openstef-beam** | Backtesting, Evaluation, Analysis, and Metrics (BEAM) |
| **openstef-meta** | Meta-learning and ensemble model architectures |
| **openstef-foundation** | Pre-trained and foundational models *(work in progress)* |

---

## How to Install

**Requirements:** Python ≥ 3.12, 64-bit OS (Windows, macOS, Linux).

```bash
# Install the complete framework
pip install openstef

# Install individual packages as needed
pip install openstef-core
pip install openstef-models
pip install openstef-beam
pip install openstef-meta

# Install with optional extras (e.g. LightGBM or XGBoost support)
pip install "openstef-models[lgbm]"
pip install "openstef-models[xgb-cpu]"
pip install "openstef-beam[all]"

# Using uv (recommended for development)
uv add openstef
```

For a full walkthrough including troubleshooting, see the [Installation Guide](https://openstef.github.io/openstef/v4/user_guide/installation.html).

---

## Examples

Runnable examples and notebooks are available in the [`examples/`](examples/) folder. See the [examples README](examples/README.md) for an overview of what is available and how to get started.

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

If you use OpenSTEF in your research, please cite the project. Citation metadata is provided in [`CITATION.cff`](CITATION.cff) at the root of this repository. Most reference managers and GitHub's *Cite this repository* button can import this file directly.

---

## Contact

- **Slack:** [LF Energy Slack](https://slack.lfenergy.org/) — `#openstef` channel
- **Email:** [openstef@lfenergy.org](mailto:openstef@lfenergy.org)
- **Community meetings:** [Four-weekly community call](https://lf-energy.atlassian.net/wiki/spaces/OS/pages/32278358/OpenSTEF+four-weekly+community+meeting)
- **Issue tracker:** [GitHub Issues](https://github.com/OpenSTEF/openstef/issues)
- **Project homepage:** [LF Energy — OpenSTEF](https://www.lfenergy.org/projects/openstef/)