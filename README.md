I now have all the information needed. The citation page uses template variables (not yet rendered), so I'll link to the canonical citation page rather than invent BibTeX values. Let me generate the complete README.

<!--
SPDX-FileCopyrightText: 2017-2025 Contributors to the OpenSTEF project <openstef@lfenergy.org>

SPDX-License-Identifier: MPL-2.0
-->

<p align="center">
  <img src="docs/source/_static/logos/openstef-horizontal-color.svg" alt="OpenSTEF" width="400"/>
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

**OpenSTEF** (Open Short-Term Energy Forecasting) is an open-source Python framework for creating accurate short-term load forecasts in the energy sector. It provides complete machine learning pipelines covering data preprocessing, feature engineering, model training, forecasting, evaluation, and post-processing. OpenSTEF generates probabilistic forecasts with uncertainty bandwidths and includes built-in domain knowledge for energy-specific use cases such as congestion management, EV charging capacity estimation, and grid loss prediction. Learn more at the [LF Energy OpenSTEF project page](https://www.lfenergy.org/projects/openstef/).

---

## Repository Structure

OpenSTEF 4.0 is organised as a monorepo workspace. Each subdirectory under `packages/` is an independently installable Python package:

| Package | Description |
|---|---|
| `openstef` | Meta-package — installs core components |
| `openstef-core` | Core utilities, dataset types, shared types, and base models |
| `openstef-models` | ML models, feature engineering, and data processing |
| `openstef-beam` | Backtesting, Evaluation, Analysis, and Metrics |
| `openstef-compatibility` | OpenSTEF 3.x compatibility layer *(coming soon)* |
| `openstef-foundational-models` | Deep learning and foundational models *(coming soon)* |

The `docs/` directory contains all documentation source, and `examples/` contains runnable example scripts and tutorials.

---

## How to Install

**Requirements:** Python 3.12+ · 64-bit OS (Windows, macOS, Linux)

```bash
# Recommended — installs openstef-core and openstef-models
pip install openstef

# Full installation including BEAM evaluation tools
pip install "openstef[all]"

# Individual packages
pip install openstef-core
pip install openstef-models
pip install openstef-beam
```

Using alternative package managers:

```bash
uv add openstef          # uv (recommended for development)
conda install -c conda-forge openstef   # conda
pixi add openstef        # pixi
```

For a complete development setup:

```bash
git clone https://github.com/OpenSTEF/openstef.git
cd openstef
uv sync --all-groups --all-extras
uv run poe all           # run linting, type checks, and tests
```

See the [full installation guide](https://openstef.github.io/openstef/v4/user_guide/installation.html) for platform-specific notes, troubleshooting, and Apple Silicon guidance.

---

## Examples

Runnable examples and step-by-step tutorials are located in the [`examples/`](examples/) directory. See the [`examples/README.md`](examples/README.md) for an overview of what is available.

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

If you use OpenSTEF in your research, please cite the project. The canonical citation (BibTeX, CFF, and DOI) is maintained on the [Citing OpenSTEF](https://openstef.github.io/openstef/v4/project/citing.html) page. A machine-readable [`CITATION.cff`](CITATION.cff) file is also available at the root of this repository.

---

## Contact

- 💬 **Slack** — [LF Energy Slack workspace](https://slack.lfenergy.org/) · `#openstef` channel
- 🐛 **Issues** — [GitHub Issue Tracker](https://github.com/OpenSTEF/openstef/issues)
- 📧 **Email** — openstef@lfenergy.org
- 🤝 **Community meetings** — four-weekly open meetings; details on the [wiki](https://wiki.lfenergy.org/display/OS/Four-weekly+community+meeting)
- 📖 **Support guide** — [openstef.github.io/openstef/v4/project/support.html](https://openstef.github.io/openstef/v4/project/support.html)