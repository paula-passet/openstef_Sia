I now have all the information needed. The citation section uses a templated CFF file (rendered at build time), so I'll point to the canonical citing page and `CITATION.cff` rather than inventing BibTeX values. Let me produce the final README.

<!--
SPDX-FileCopyrightText: 2017-2025 Contributors to the OpenSTEF project <openstef@lfenergy.org>

SPDX-License-Identifier: MPL-2.0
-->

<p align="center">
  <img src="docs/source/_static/logos/openstef-horizontal-color.svg" alt="OpenSTEF logo" width="400"/>
</p>

<p align="center">
  <a href="https://pepy.tech/project/openstef"><img src="https://static.pepy.tech/badge/openstef" alt="Total downloads"/></a>
  <a href="https://pepy.tech/project/openstef"><img src="https://static.pepy.tech/badge/openstef/month" alt="Monthly downloads"/></a>
  <a href="https://bestpractices.coreinfrastructure.org/projects/5585"><img src="https://bestpractices.coreinfrastructure.org/projects/5585/badge" alt="CII Best Practices"/></a>
  <a href="https://pypi.org/project/openstef/"><img src="https://img.shields.io/badge/version-4.0.0-blue" alt="Version 4.0.0"/></a>
  <a href="LICENSE.md"><img src="https://img.shields.io/badge/license-MPL--2.0-green" alt="License: MPL-2.0"/></a>
</p>

---

## What is OpenSTEF?

**OpenSTEF** (Open Short-Term Energy Forecasting) is an open-source Python framework for creating accurate short-term load forecasts in the energy sector. It provides complete machine learning pipelines — from data preprocessing and feature engineering through model training, probabilistic forecasting, and post-processing — all with built-in domain knowledge for energy use cases. OpenSTEF is model-agnostic and production-proven, currently generating forecasts for over 10,000 grid locations. Learn more at the [LF Energy OpenSTEF project page](https://www.lfenergy.org/projects/openstef/).

---

## Repository Structure

OpenSTEF 4.0 is organised as a monorepo workspace. Each subdirectory under `packages/` is an independently installable Python package:

| Package | Description |
|---|---|
| `openstef` | Meta-package — installs the core components |
| `openstef-core` | Core utilities, dataset types, shared types and base models |
| `openstef-models` | ML models, feature engineering, and data processing |
| `openstef-beam` | Backtesting, Evaluation, Analysis, and Metrics |
| `openstef-compatibility` | OpenSTEF 3.x compatibility layer *(coming soon)* |
| `openstef-foundational-models` | Deep learning and foundational models *(coming soon)* |

The `docs/` directory contains all documentation source, and `examples/` contains runnable example scripts and tutorials.

---

## Installation

**Requirements:** Python 3.12+ · 64-bit OS (Windows, macOS, Linux)

```bash
# Recommended — installs openstef-core and openstef-models
pip install openstef

# All optional components (adds openstef-beam)
pip install "openstef[all]"

# Individual packages
pip install openstef-core
pip install openstef-models
pip install openstef-beam
```

Using alternative package managers:

```bash
uv add openstef          # uv (recommended for development)
conda install -c conda-forge openstef
pixi add openstef
```

For platform-specific notes (Apple Silicon, GPU, WSL) and a full development-environment setup, see the **[Installation Guide](https://openstef.github.io/openstef/v4/user_guide/installation.html)**.

---

## Examples

Runnable examples and step-by-step tutorials live in the [`examples/`](examples/) directory. See the [`examples/README.md`](examples/README.md) for an overview of what is available.

Additional learning resources:

- **[Quick Start Guide](https://openstef.github.io/openstef/v4/user_guide/quick_start.html)**
- **[Tutorials](https://openstef.github.io/openstef/v4/user_guide/tutorials.html)**
- **[API Reference](https://openstef.github.io/openstef/v4/api/)**

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

If you use OpenSTEF in your research, please cite it. The canonical citation metadata is maintained in [`CITATION.cff`](CITATION.cff) at the root of this repository.

For a formatted BibTeX entry and DOI badge, see the **[Citing OpenSTEF](https://openstef.github.io/openstef/v4/project/citing.html)** page in the documentation.

---

## Contact

- 💬 **Slack** — [LF Energy Slack workspace](https://slack.lfenergy.org/) · `#openstef` channel
- 🐛 **Issues** — [GitHub Issue Tracker](https://github.com/OpenSTEF/openstef/issues)
- 📧 **Email** — openstef@lfenergy.org
- 🤝 **Community meetings** — four-weekly open calls; details on the [wiki](https://wiki.lfenergy.org/display/OS/Four-weekly+community+meeting)
- 📖 **Support page** — [openstef.github.io/openstef/v4/project/support.html](https://openstef.github.io/openstef/v4/project/support.html)