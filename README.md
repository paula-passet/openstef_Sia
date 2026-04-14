I now have all the information needed. Here is the complete, production-ready README.md:

<!--
SPDX-FileCopyrightText: 2017-2025 Contributors to the OpenSTEF project <openstef@lfenergy.org>

SPDX-License-Identifier: MPL-2.0
-->

<p align="center">
  <img src="docs/source/logos/openstef-horizontal-color.svg" alt="OpenSTEF logo" width="400"/>
</p>

---

[![Downloads](https://static.pepy.tech/badge/openstef)](https://pepy.tech/project/openstef)
[![Downloads](https://static.pepy.tech/badge/openstef/month)](https://pepy.tech/project/openstef)
[![CII Best Practices](https://bestpractices.coreinfrastructure.org/projects/5585/badge)](https://bestpractices.coreinfrastructure.org/projects/5585)
[![PyPI version](https://img.shields.io/pypi/v/openstef.svg)](https://pypi.org/project/openstef/)
[![License: MPL 2.0](https://img.shields.io/badge/License-MPL_2.0-brightgreen.svg)](LICENSE.md)

---

## What is OpenSTEF

**OpenSTEF** (Open Short-Term Energy Forecasting) is an open-source Python library for creating accurate short-term load forecasts in the energy sector. It provides a complete, model-agnostic machine learning pipeline covering data preprocessing, feature engineering, model training, probabilistic forecasting, evaluation, and post-processing. OpenSTEF supports use cases including congestion management, transport forecasting, EV charging capacity estimation, and grid loss prediction. For more information, visit the [OpenSTEF project homepage](https://www.lfenergy.org/projects/openstef/).

---

## Repository Structure

OpenSTEF 4.0 uses a **monorepo workspace** with specialized, independently installable packages:

| Package | Description |
|---|---|
| `openstef` | Meta-package — installs core components |
| `openstef-core` | Core utilities, dataset types, shared types and base models |
| `openstef-models` | ML models, feature engineering, and data processing |
| `openstef-beam` | Backtesting, Evaluation, Analysis, and Metrics (BEAM) |
| `openstef-compatibility` | OpenSTEF 3.x compatibility layer *(coming soon)* |
| `openstef-foundational-models` | Deep learning and foundational models *(coming soon)* |

All packages are developed together under a single `pyproject.toml` workspace. Changes in one package are immediately available to others during development. See the [architecture documentation](https://openstef.github.io/openstef/v4/user_guide/installation.html#package-architecture) for details.

---

## How to Install

**Requirements:** Python 3.12+ · 64-bit OS (Windows, macOS, Linux)

```bash
# Recommended for most users
pip install openstef

# Install all optional components
pip install "openstef[all]"

# Individual packages
pip install openstef-core       # Shared utilities only
pip install openstef-models     # Core forecasting models only
pip install openstef-beam       # Backtesting and evaluation only
```

```bash
# Using uv (recommended for development)
uv add openstef

# Using conda
conda install -c conda-forge openstef

# Using pixi
pixi add openstef
```

For troubleshooting (Apple Silicon, GPU support, Python version management) see the [complete installation guide](https://openstef.github.io/openstef/v4/user_guide/installation.html).

---

## Examples

Hands-on examples and tutorials are available in the [`examples/`](examples/) folder. See the [`examples/README.md`](examples/README.md) for an overview of what is available.

Additional step-by-step tutorials are published in the [online documentation](https://openstef.github.io/openstef/v4/user_guide/tutorials.html).

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

If you use OpenSTEF in your research, please cite the project. A machine-readable citation file is provided at [`CITATION.cff`](CITATION.cff). You can also cite via the project DOI on [Zenodo](https://zenodo.org) or reference the GitHub repository directly.

Full citation details, including a BibTeX entry and DOI badge, are available on the [Citing OpenSTEF](https://openstef.github.io/openstef/v4/project/citing.html) page.

---

## Contact & Support

- 💬 **Slack** — Join the `#openstef` channel in the [LF Energy Slack workspace](https://slack.lfenergy.org/)
- 🐛 **Issue Tracker** — [GitHub Issues](https://github.com/OpenSTEF/openstef/issues) for bug reports and feature requests
- 📧 **Email** — [openstef@lfenergy.org](mailto:openstef@lfenergy.org)
- 🤝 **Community Meetings** — Four-weekly open meetings; details on the [LF Energy wiki](https://wiki.lfenergy.org/display/OS/Four-weekly+community+meeting)
- 📖 **Support Guide** — [openstef.github.io/openstef/v4/project/support](https://openstef.github.io/openstef/v4/project/support.html)