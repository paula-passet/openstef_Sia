<!--
SPDX-FileCopyrightText: 2017-2025 Contributors to the OpenSTEF project <openstef@lfenergy.org>

SPDX-License-Identifier: MPL-2.0
-->

<p align="center">
  <img src="https://raw.githubusercontent.com/OpenSTEF/.github/main/profile/assets/openstef_logo.png" alt="OpenSTEF logo" width="400"/>
</p>

<p align="center">
  <a href="https://pepy.tech/project/openstef"><img src="https://static.pepy.tech/badge/openstef" alt="Downloads"/></a>
  <a href="https://pepy.tech/project/openstef"><img src="https://static.pepy.tech/badge/openstef/month" alt="Downloads per month"/></a>
  <a href="https://bestpractices.coreinfrastructure.org/projects/5585"><img src="https://bestpractices.coreinfrastructure.org/projects/5585/badge" alt="CII Best Practices"/></a>
  <a href="https://github.com/paula-passet/openstef_Sia/releases/tag/release/v4.0.0"><img src="https://img.shields.io/badge/release-v4.0.0-blue" alt="Release v4.0.0"/></a>
  <a href="LICENSE.md"><img src="https://img.shields.io/badge/license-MPL--2.0-brightgreen" alt="License: MPL-2.0"/></a>
</p>

---

## What is OpenSTEF?

**OpenSTEF** (Open Short-Term Energy Forecasting) is an open-source Python framework for generating accurate short-term energy load forecasts hours to days ahead. It provides complete, model-agnostic machine learning pipelines covering data preprocessing, feature engineering, model training, probabilistic forecasting, evaluation, and post-processing. Built-in domain knowledge — such as solar radiation to PV generation estimates — makes it immediately applicable to congestion management, transport forecasting, EV charging capacity estimation, and grid loss prediction. For more information, visit the [LF Energy OpenSTEF project page](https://www.lfenergy.org/projects/openstef/).

---

## Repository Structure

OpenSTEF 4.0 is organised as a **modular monorepo**. Each package is self-contained and can be installed independently:

| Package | Description |
|---|---|
| **`openstef`** | Meta-package — installs the full framework (`openstef-beam`, `openstef-core`, `openstef-meta`, `openstef-models`) |
| **`openstef-core`** | Shared data types, base classes, interfaces, and testing utilities |
| **`openstef-models`** | Forecasting models, feature engineering, data preprocessing pipelines, and explainability |
| **`openstef-meta`** | Meta-learning and ensemble model architectures |
| **`openstef-beam`** | Backtesting, Evaluation, Analysis, and Metrics (BEAM) |

---

## Installation

**Requirements:** Python ≥ 3.12, 64-bit OS (Windows, macOS, Linux).

```bash
# Install the complete framework
pip install openstef

# Install individual packages
pip install openstef-models
pip install openstef-beam

# Install with optional extras
pip install "openstef-beam[all]"
pip install "openstef-models[lgbm]"
pip install "openstef-models[xgb-cpu]"

# Using uv (recommended for development)
uv add openstef
```

See the [Installation Guide](https://openstef.github.io/openstef/v4/user_guide/installation.html) for full details, including optional model backends and development setup.

---

## Examples

Runnable examples are in the [`examples/`](examples/) folder. See the [examples README](examples/README.md) for an overview of available notebooks and scripts covering common forecasting workflows.

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

If you use OpenSTEF in your research, please cite the project. Citation metadata is provided in [`CITATION.cff`](CITATION.cff) at the root of this repository. GitHub renders a **Cite this repository** button on the repository sidebar that generates APA and BibTeX entries automatically from that file.

---

## Contact

- **Slack:** [LF Energy Slack](https://slack.lfenergy.org/) — `#openstef` channel
- **Email:** [openstef@lfenergy.org](mailto:openstef@lfenergy.org)
- **Community meetings:** [OpenSTEF four-weekly community meeting](https://lf-energy.atlassian.net/wiki/spaces/OS/pages/32278358/OpenSTEF+four-weekly+community+meeting)
- **Issue tracker:** [github.com/OpenSTEF/openstef/issues](https://github.com/OpenSTEF/openstef/issues)