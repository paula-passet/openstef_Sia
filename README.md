I now have all the information needed. Let me produce the complete README.md.

<!--
SPDX-FileCopyrightText: 2017-2025 Contributors to the OpenSTEF project <openstef@lfenergy.org>

SPDX-License-Identifier: MPL-2.0
-->

<p align="center">
  <img src="docs/logos/openstef-horizontal-color.svg" alt="OpenSTEF" width="400"/>
</p>

<p align="center">
  <a href="https://pepy.tech/project/openstef"><img src="https://static.pepy.tech/badge/openstef" alt="Downloads"/></a>
  <a href="https://pepy.tech/project/openstef"><img src="https://static.pepy.tech/badge/openstef/month" alt="Downloads per month"/></a>
  <a href="https://bestpractices.coreinfrastructure.org/projects/5585"><img src="https://bestpractices.coreinfrastructure.org/projects/5585/badge" alt="CII Best Practices"/></a>
  <a href="https://github.com/paula-passet/openstef_Sia/releases/tag/release/v4.0.0"><img src="https://img.shields.io/badge/release-v4.0.0-blue" alt="Release v4.0.0"/></a>
  <a href="LICENSE.md"><img src="https://img.shields.io/badge/license-MPL--2.0-green" alt="License: MPL-2.0"/></a>
</p>

---

## What is OpenSTEF

**OpenSTEF** (Open Short-Term Energy Forecasting) is an open-source Python framework for creating accurate short-term energy forecasts in the power grid domain. It provides complete, model-agnostic pipelines covering data preprocessing, feature engineering, model training, probabilistic forecasting, evaluation, and post-processing. OpenSTEF is designed for use cases including congestion management, transport forecasts, grid loss prediction, and EV charging capacity estimation. For more information, visit the [OpenSTEF project homepage](https://www.lfenergy.org/projects/openstef/).

---

## Repository Structure

OpenSTEF v4.0.0 is organised as a **modular monorepo**. Each sub-package is independently installable and has a focused responsibility:

| Package | Description |
|---|---|
| **`openstef`** | Meta-package — installs the full framework (`openstef-beam`, `openstef-core`, `openstef-meta`, `openstef-models`) |
| **`openstef-core`** | Core data types, interfaces, base classes, and shared utilities used by all other packages |
| **`openstef-models`** | Forecasting models, data preprocessing pipelines, energy-specific feature engineering, and explainability |
| **`openstef-beam`** | Backtesting, Evaluation, Analysis, and Metrics (BEAM) |
| **`openstef-meta`** | Meta-learning models and modern ensemble architectures |

---

## How to Install

**Requirements:** Python `>=3.12,<4.0` · 64-bit OS (Windows, macOS, Linux)

```bash
# Install the complete framework
pip install openstef

# Or install only the packages you need
pip install openstef-core
pip install openstef-models
pip install openstef-beam
pip install openstef-meta

# With optional extras (e.g. LightGBM support)
pip install "openstef-models[lgbm]"

# Using uv (recommended for development)
uv add openstef
```

For a full development setup:

```bash
git clone https://github.com/paula-passet/openstef_Sia.git
cd openstef_Sia
uv sync --dev
uv run poe all   # run tests and quality checks
```

See the [Installation Guide](https://openstef.github.io/openstef/v4/user_guide/installation.html) for detailed instructions including optional extras, GPU support, and troubleshooting.

---

## Examples

Ready-to-run examples are in the [`examples/`](examples/) folder. See [`examples/README.md`](examples/README.md) for an overview of available notebooks and scripts.

To install all example dependencies:

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

If you use OpenSTEF in your research, please cite the project. Citation metadata is provided in [`CITATION.cff`](CITATION.cff). GitHub will render a formatted citation automatically via the **"Cite this repository"** button, or you can export BibTeX directly from that file.

---

## Contact

- **Slack:** [LF Energy Slack](https://slack.lfenergy.org/) — `#openstef` channel
- **Email:** [openstef@lfenergy.org](mailto:openstef@lfenergy.org)
- **Community meetings:** [Four-weekly OpenSTEF community call](https://lf-energy.atlassian.net/wiki/spaces/OS/pages/32278358/OpenSTEF+four-weekly+community+meeting)
- **Issue tracker:** [GitHub Issues](https://github.com/OpenSTEF/openstef/issues)
- **Project homepage:** [LF Energy — OpenSTEF](https://www.lfenergy.org/projects/openstef/)