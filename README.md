I now have all the information needed. Let me compile the complete, accurate README.md.

<!--
SPDX-FileCopyrightText: 2017-2025 Contributors to the OpenSTEF project <openstef@lfenergy.org>

SPDX-License-Identifier: MPL-2.0
-->

<p align="center">
  <img src="docs/logos/openstef-horizontal-color.svg" alt="OpenSTEF" width="400"/>
</p>

---

[![Downloads](https://static.pepy.tech/badge/openstef)](https://pepy.tech/project/openstef)
[![Downloads](https://static.pepy.tech/badge/openstef/month)](https://pepy.tech/project/openstef)
[![CII Best Practices](https://bestpractices.coreinfrastructure.org/projects/5585/badge)](https://bestpractices.coreinfrastructure.org/projects/5585)
[![License: MPL-2.0](https://img.shields.io/badge/License-MPL%202.0-brightgreen.svg)](LICENSE.md)
[![Release](https://img.shields.io/badge/release-v4.0.0-blue)](https://github.com/paula-passet/openstef_Sia/releases/tag/release/v4.0.0)

---

## What is OpenSTEF

**OpenSTEF** (Open Short-Term Energy Forecasting) is an open-source Python framework for creating accurate short-term load forecasts in the power grid domain. It provides complete, model-agnostic pipelines covering data preprocessing, feature engineering, model training, probabilistic forecasting, evaluation, and post-processing. OpenSTEF is designed for use cases including congestion management, transport forecasting, grid loss prediction, and beyond. Learn more at the [LF Energy OpenSTEF project page](https://www.lfenergy.org/projects/openstef/).

---

## Repository Structure

OpenSTEF 4.0 is organised as a **modular monorepo**. Each sub-package is self-contained and can be installed independently:

| Package | Description |
|---|---|
| **`openstef`** | Meta-package — installs the full framework (`openstef-core`, `openstef-models`, `openstef-beam`, `openstef-meta`) |
| **`openstef-core`** | Core data types, interfaces, base classes, and shared utilities |
| **`openstef-models`** | Forecasting models, feature engineering, data preprocessing, and explainability |
| **`openstef-beam`** | Backtesting, Evaluation, Analysis, and Metrics (BEAM) |
| **`openstef-meta`** | Meta-learning and ensemble forecasting models |

---

## How to Install

**Requirements:** Python ≥ 3.12, < 4.0 · 64-bit OS (Windows, macOS, Linux)

```bash
# Install the full framework
pip install openstef

# Or install only the packages you need
pip install openstef-core
pip install openstef-models
pip install openstef-beam
pip install openstef-meta

# With optional extras (e.g. LightGBM support)
pip install "openstef-models[lgbm]"

# Install everything including all optional extras
pip install "openstef-beam[all]"
```

For development, install all packages and dependencies in one step:

```bash
git clone https://github.com/OpenSTEF/openstef.git
cd openstef
uv sync --dev
```

---

## Examples

Ready-to-run examples are in the [`examples/`](examples/) folder. See [`examples/README.md`](examples/README.md) for an overview of all available examples.

To install the dependencies required to run the examples:

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

If you use OpenSTEF in your research, please cite it using the metadata in [`CITATION.cff`](CITATION.cff). Most reference managers and GitHub's *Cite this repository* button can export this automatically. A BibTeX entry is generated from that file and is also available in the [project documentation](https://openstef.github.io/openstef/v4/).

---

## Contact

- **Slack:** [LF Energy Slack](https://slack.lfenergy.org/) — find the `#openstef` channel
- **Email:** [openstef@lfenergy.org](mailto:openstef@lfenergy.org)
- **Community meetings:** [OpenSTEF four-weekly community meeting](https://lf-energy.atlassian.net/wiki/spaces/OS/pages/32278358/OpenSTEF+four-weekly+community+meeting)
- **Issue Tracker:** [github.com/OpenSTEF/openstef/issues](https://github.com/OpenSTEF/openstef/issues)