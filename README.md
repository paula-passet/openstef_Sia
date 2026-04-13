I now have all the information needed. Let me produce the complete, production-ready README.md.

<!--
SPDX-FileCopyrightText: 2017-2025 Contributors to the OpenSTEF project <openstef@lfenergy.org>

SPDX-License-Identifier: MPL-2.0
-->

<p align="center">
  <img src="docs/source/_static/logos/openstef-horizontal-color.svg" alt="OpenSTEF homepage" width="400"/>
</p>

<p align="center">
  <a href="https://pepy.tech/project/openstef"><img src="https://static.pepy.tech/badge/openstef" alt="Downloads"/></a>
  <a href="https://pepy.tech/project/openstef"><img src="https://static.pepy.tech/badge/openstef/month" alt="Downloads per month"/></a>
  <a href="https://bestpractices.coreinfrastructure.org/projects/5585"><img src="https://bestpractices.coreinfrastructure.org/projects/5585/badge" alt="CII Best Practices"/></a>
  <a href="https://pypi.org/project/openstef/"><img src="https://img.shields.io/badge/version-4.0.0-blue" alt="Version 4.0.0"/></a>
  <a href="LICENSE.md"><img src="https://img.shields.io/badge/license-MPL--2.0-green" alt="License: MPL-2.0"/></a>
</p>

---

## What is OpenSTEF?

**OpenSTEF** (Open Short-Term Energy Forecasting) is an open-source Python framework for creating accurate short-term load forecasts in the energy sector. It provides a complete, model-agnostic machine learning pipeline covering data preprocessing, feature engineering, model training, forecasting, evaluation, and post-processing. OpenSTEF generates probabilistic forecasts with uncertainty bandwidths and includes built-in domain knowledge for energy-specific use cases such as congestion management, EV charging capacity estimation, and grid loss prediction. Learn more at the [LF Energy OpenSTEF project page](https://www.lfenergy.org/projects/openstef/).

---

## Repository Structure

OpenSTEF 4.0 is organised as a monorepo workspace. Each concern lives in its own installable package under `packages/`:

| Package | Description |
|---|---|
| `openstef` | Meta-package — installs the core components |
| `openstef-core` | Core utilities, dataset types, shared types and base models |
| `openstef-models` | ML models, feature engineering, and data processing |
| `openstef-beam` | Backtesting, Evaluation, Analysis, and Metrics (BEAM) |
| `openstef-compatibility` | OpenSTEF 3.x compatibility layer *(coming soon)* |
| `openstef-foundational-models` | Deep learning and foundational models *(coming soon)* |

The `docs/` directory contains all documentation source, and `examples/` contains runnable example scripts and tutorials.

---

## Installation

**Requirements:** Python 3.12+ · 64-bit OS (Windows, macOS, Linux)

```bash
# Recommended — installs openstef-core and openstef-models
pip install openstef

# All available extras (adds openstef-beam)
pip install "openstef[all]"

# Individual packages
pip install openstef-core
pip install openstef-models
pip install openstef-beam
```

Using alternative package managers:

```bash
uv add openstef            # uv (recommended for development)
conda install -c conda-forge openstef   # conda
pixi add openstef          # pixi
```

For a full guide including Apple Silicon notes, GPU support, and troubleshooting, see the **[Installation Guide](https://openstef.github.io/openstef/v4/user_guide/installation.html)**.

---

## Examples

Runnable examples and tutorials live in the [`examples/`](examples/) folder. See the [`examples/README.md`](examples/README.md) for an overview of all available examples.

Step-by-step tutorials are also available in the **[online documentation](https://openstef.github.io/openstef/v4/user_guide/tutorials.html)**.

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

If you use OpenSTEF in your research, please cite the project. A machine-readable citation file is available at [`CITATION.cff`](CITATION.cff). The full BibTeX entry and DOI are documented on the **[Citing OpenSTEF](https://openstef.github.io/openstef/v4/project/citing.html)** page.

---

## Contact

- 💬 **Slack** — [LF Energy Slack workspace](https://slack.lfenergy.org/) (`#openstef` channel)
- 🐛 **Issues** — [GitHub Issues](https://github.com/OpenSTEF/openstef/issues)
- 📧 **Email** — [openstef@lfenergy.org](mailto:openstef@lfenergy.org)
- 🤝 **Community meetings** — four-weekly open sessions; details on the [community meeting wiki](https://lf-energy.atlassian.net/wiki/spaces/OS/pages/32278358/OpenSTEF+four-weekly+community+meeting)

For a full overview of support channels, see the **[Support page](https://openstef.github.io/openstef/v4/project/support.html)**.