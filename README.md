I now have all the information needed. Let me produce the final README.md.

<!--
SPDX-FileCopyrightText: 2017-2025 Contributors to the OpenSTEF project <openstef@lfenergy.org>

SPDX-License-Identifier: MPL-2.0
-->

<p align="center">
  <img src="docs/source/_static/logos/openstef-horizontal-color.svg" alt="OpenSTEF homepage" width="400"/>
</p>

---

[![Downloads](https://static.pepy.tech/badge/openstef)](https://pepy.tech/project/openstef)
[![Downloads](https://static.pepy.tech/badge/openstef/month)](https://pepy.tech/project/openstef)
[![CII Best Practices](https://bestpractices.coreinfrastructure.org/projects/5585/badge)](https://bestpractices.coreinfrastructure.org/projects/5585)
[![PyPI version](https://img.shields.io/pypi/v/openstef.svg)](https://pypi.org/project/openstef/)
[![License: MPL 2.0](https://img.shields.io/badge/License-MPL_2.0-brightgreen.svg)](LICENSE.md)

---

## What is OpenSTEF?

**OpenSTEF** (Open Short-Term Energy Forecasting) is an open-source Python framework for creating accurate short-term load forecasts in the energy sector. It is model-agnostic and provides complete machine learning pipelines covering data preprocessing, feature engineering, model training, probabilistic forecasting, evaluation, and post-processing. OpenSTEF includes built-in domain knowledge for energy-specific features such as solar radiation and PV generation estimates, and is already running in production at scale for congestion management across 10,000+ grid locations. For more information, visit the [OpenSTEF project page](https://www.lfenergy.org/projects/openstef/).

---

## Repository Structure

OpenSTEF 4.0 is organised as a **monorepo workspace** containing the following packages:

| Package | Description |
|---|---|
| `openstef` | Meta-package — installs the core components |
| `openstef-core` | Core utilities, dataset types, shared types and base models |
| `openstef-models` | ML models, feature engineering, and data processing |
| `openstef-beam` | Backtesting, Evaluation, Analysis, and Metrics (BEAM) |
| `openstef-compatibility` | Compatibility layer for OpenSTEF 3.x *(coming soon)* |
| `openstef-foundational-models` | Deep learning and foundational models *(coming soon)* |

Changes to `openstef-core` can impact both `openstef-models` and `openstef-beam`; always test all affected packages when working across boundaries. See the [architecture documentation](https://openstef.github.io/openstef/v4/user_guide/installation.html#package-architecture) for details.

---

## Installation

**Requirements:** Python 3.12+ · 64-bit OS (Windows, macOS, Linux)

```bash
# pip
pip install openstef

# uv (recommended for development)
uv add openstef

# conda
conda install -c conda-forge openstef

# pixi
pixi add openstef
```

Install individual packages when you only need a subset of functionality:

```bash
pip install openstef-models   # ML models and feature engineering only
pip install openstef-beam     # Backtesting, evaluation, and metrics only
```

For a full development setup:

```bash
git clone https://github.com/OpenSTEF/openstef.git
cd openstef
uv sync --all-groups --all-extras   # installs all packages, dev tools, and pre-commit hooks
uv run poe all                      # lint, format, type-check, and test
```

See the [complete installation guide](https://openstef.github.io/openstef/v4/user_guide/installation.html) for troubleshooting, Apple Silicon notes, and GPU support.

---

## Examples

Ready-to-run examples and step-by-step tutorials live in the [`examples/`](examples/) directory. Refer to the [`examples/README.md`](examples/README.md) for an overview of all available examples.

Additional learning resources:

- [Quick Start Guide](https://openstef.github.io/openstef/v4/user_guide/quick_start.html)
- [Tutorials](https://openstef.github.io/openstef/v4/user_guide/tutorials.html)
- [API Reference](https://openstef.github.io/openstef/v4/api/)

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

If you use OpenSTEF in your research, please cite the project. The canonical citation file is [`CITATION.cff`](CITATION.cff). A DOI badge and a ready-to-use BibTeX entry are available on the [Citing OpenSTEF](https://openstef.github.io/openstef/v4/project/citing.html) documentation page.

---

## Contact

- 💬 **Slack** — `#openstef` channel in the [LF Energy Slack workspace](https://slack.lfenergy.org/) (email [openstef@lfenergy.org](mailto:openstef@lfenergy.org) to request an invite)
- 🐛 **Issues** — [GitHub Issue Tracker](https://github.com/OpenSTEF/openstef/issues)
- 📧 **Email** — [openstef@lfenergy.org](mailto:openstef@lfenergy.org)
- 🤝 **Community meetings** — four-weekly open calls; details on the [LF Energy wiki](https://wiki.lfenergy.org/display/OS/Four-weekly+community+meeting)
- 🌐 **Project homepage** — [LF Energy OpenSTEF](https://www.lfenergy.org/projects/openstef/)

Full support information is available on the [Support page](https://openstef.github.io/openstef/v4/project/support.html).