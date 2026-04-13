I now have all the information needed to produce a complete, accurate README. Here it is:

<!--
SPDX-FileCopyrightText: 2017-2025 Contributors to the OpenSTEF project <openstef@lfenergy.org>

SPDX-License-Identifier: MPL-2.0
-->

<p align="center">
  <img src="docs/source/_static/logos/openstef-horizontal-color.svg" alt="OpenSTEF homepage" width="400"/>
</p>

# OpenSTEF

[![Downloads](https://static.pepy.tech/badge/openstef)](https://pepy.tech/project/openstef)
[![Downloads](https://static.pepy.tech/badge/openstef/month)](https://pepy.tech/project/openstef)
[![CII Best Practices](https://bestpractices.coreinfrastructure.org/projects/5585/badge)](https://bestpractices.coreinfrastructure.org/projects/5585)
[![PyPI version](https://img.shields.io/badge/release-v4.0.0-blue)](https://github.com/paula-passet/openstef_Sia/releases/tag/release/v4.0.0)
[![License: MPL 2.0](https://img.shields.io/badge/License-MPL_2.0-brightgreen.svg)](LICENSE.md)

## What is OpenSTEF

**OpenSTEF** (Open Short-Term Energy Forecasting) is an open-source Python library for creating accurate short-term load forecasts in the energy sector — covering use cases such as congestion management, transport forecasts, EV charging capacity estimation, and grid loss prediction. It is a model-agnostic machine learning framework that provides complete pipelines for data preprocessing, feature engineering, model training, forecasting, evaluation, and post-processing, including probabilistic forecasts with uncertainty bandwidths. OpenSTEF 4.0 introduces a fully modular architecture with comprehensive type safety, modern tooling, and a monorepo workspace structure. For more information, visit the [OpenSTEF project page](https://www.lfenergy.org/projects/openstef/).

## Repository Structure

OpenSTEF 4.0 is organised as a monorepo workspace. Each subdirectory under `packages/` is an independently installable Python package:

| Package | Description |
|---|---|
| `openstef` | Meta-package — installs core components |
| `openstef-core` | Core utilities, dataset types, shared types, and base models |
| `openstef-models` | ML models, feature engineering, and data processing |
| `openstef-beam` | Backtesting, Evaluation, Analysis, and Metrics |
| `openstef-compatibility` | Compatibility layer for OpenSTEF 3.x *(coming soon)* |
| `openstef-foundational-models` | Deep learning and foundational models *(coming soon)* |

The `docs/` directory contains the full documentation source, and `examples/` contains runnable example scripts and tutorials.

## How to Install

**Requirements:** Python 3.12+ · 64-bit OS (Windows, macOS, Linux)

```bash
# Recommended for most users
pip install openstef

# Install all available extras (openstef-models + openstef-beam)
pip install "openstef[all]"

# Install individual packages
pip install openstef-core
pip install openstef-models
pip install openstef-beam

# Using uv (recommended for development)
uv add openstef

# Using conda
conda install -c conda-forge openstef
```

See the **[complete Installation Guide](https://openstef.github.io/openstef/v4/user_guide/installation.html)** for platform-specific notes, troubleshooting, and development setup instructions.

## Examples

Runnable examples and tutorials are located in the [`examples/`](examples/) folder. See the [`examples/README.md`](examples/README.md) for an overview of available examples.

Additional learning resources:

- **[Quick Start Guide](https://openstef.github.io/openstef/v4/user_guide/quick_start.html)**
- **[Tutorials](https://openstef.github.io/openstef/v4/user_guide/tutorials.html)**
- **[API Reference](https://openstef.github.io/openstef/v4/api/)**

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

If you use OpenSTEF in your research, please cite the project. The canonical citation information is maintained in [`CITATION.cff`](CITATION.cff). You can also cite via the Zenodo DOI or reference the GitHub repository directly.

See the **[Citing OpenSTEF](https://openstef.github.io/openstef/v4/project/citing.html)** page for the full BibTeX entry, DOI badge, and downloadable CFF file.

## Contact

- 💬 **Slack:** [LF Energy Slack workspace](https://slack.lfenergy.org/) — `#openstef` channel
- 🐛 **Issues:** [GitHub Issue Tracker](https://github.com/OpenSTEF/openstef/issues)
- 📧 **Email:** [openstef@lfenergy.org](mailto:openstef@lfenergy.org)
- 🤝 **Community meetings:** Four-weekly open meetings — details on the [LF Energy wiki](https://wiki.lfenergy.org/display/OS/Four-weekly+community+meeting)
- 📖 **Support page:** [openstef.github.io/openstef/v4/project/support.html](https://openstef.github.io/openstef/v4/project/support.html)