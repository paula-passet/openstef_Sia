<!--
SPDX-FileCopyrightText: 2017-2025 Contributors to the OpenSTEF project <openstef@lfenergy.org>

SPDX-License-Identifier: MPL-2.0
-->

<p align="center">
  <img src="docs/logos/openstef-horizontal-color.svg" alt="OpenSTEF logo" width="400"/>
</p>

---

[![Downloads](https://static.pepy.tech/badge/openstef)](https://pepy.tech/project/openstef)
[![Downloads](https://static.pepy.tech/badge/openstef/month)](https://pepy.tech/project/openstef)
[![CII Best Practices](https://bestpractices.coreinfrastructure.org/projects/5585/badge)](https://bestpractices.coreinfrastructure.org/projects/5585)
[![License: MPL-2.0](https://img.shields.io/badge/License-MPL%202.0-brightgreen.svg)](LICENSE.md)
[![Release](https://img.shields.io/badge/release-v4.0.0-blue)](https://github.com/paula-passet/openstef_Sia/releases/tag/release/v4.0.0)

---

## What is OpenSTEF?

**OpenSTEF** (Open Short-Term Energy Forecasting) is an open-source Python library that provides complete machine learning pipelines for accurate short-term energy load forecasting — covering data preprocessing, feature engineering, model training, probabilistic forecasting, evaluation, and post-processing. It is model-agnostic, includes built-in domain knowledge for the energy sector, and is designed to support use cases such as congestion management, transport forecasting, and grid loss prediction. Version 4.0 is a major architectural refactor introducing a modular monorepo structure with full type safety and modern Python tooling. For more information, visit the [LF Energy OpenSTEF project page](https://www.lfenergy.org/projects/openstef/).

---

## Repository Structure

OpenSTEF 4.0 is organised as a monorepo containing the following packages:

| Package | Description | Install |
|---|---|---|
| **openstef** | Meta-package — installs the full framework | `pip install openstef` |
| **openstef-core** | Core data types, interfaces, base classes, and shared utilities | `pip install openstef-core` |
| **openstef-models** | Forecasting models, feature engineering, and data preprocessing pipelines | `pip install openstef-models` |
| **openstef-meta** | Meta-learning models and advanced model architectures | `pip install openstef-meta` |
| **openstef-beam** | Backtesting, Evaluation, Analysis, and Metrics (BEAM) | `pip install openstef-beam` |

Each package can be used independently or composed together. See the [architecture documentation](https://openstef.github.io/openstef/v4/user_guide/installation.html#package-architecture) for details.

---

## How to Install

**Requirements:** Python ≥ 3.12, < 4.0 · 64-bit OS (Windows, macOS, Linux)

```bash
# Install the full framework
pip install openstef

# Or install only the packages you need
pip install openstef-models
pip install openstef-beam
pip install openstef-core

# Using uv (recommended for development)
uv sync --all-extras --all-groups --all-packages
```

For a complete installation guide including troubleshooting and development setup, see the [Installation Guide](https://openstef.github.io/openstef/v4/user_guide/installation.html).

---

## Examples

Runnable examples are available in the [`examples/`](examples/) folder. See [`examples/README.md`](examples/README.md) for an overview of available examples and setup instructions.

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

If you use OpenSTEF in your research, please cite the project. Citation metadata is provided in [`CITATION.cff`](CITATION.cff) at the root of this repository. BibTeX can be generated automatically from that file, or via the **"Cite this repository"** button on GitHub.

---

## Contact

- **Slack:** [LF Energy Slack](https://slack.lfenergy.org/) — `#openstef` channel
- **Email:** [openstef@lfenergy.org](mailto:openstef@lfenergy.org)
- **Community meetings:** [OpenSTEF four-weekly community meeting](https://lf-energy.atlassian.net/wiki/spaces/OS/pages/32278358/OpenSTEF+four-weekly+community+meeting)
- **Issue tracker:** [github.com/OpenSTEF/openstef/issues](https://github.com/OpenSTEF/openstef/issues)