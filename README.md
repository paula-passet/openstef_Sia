I now have all the information needed to produce the complete, accurate README. Let me compile it.

<!--
SPDX-FileCopyrightText: 2017-2025 Contributors to the OpenSTEF project <openstef@lfenergy.org>

SPDX-License-Identifier: MPL-2.0
-->

<p align="center">
  <img src="https://raw.githubusercontent.com/OpenSTEF/openstef/main/docs/logos/openstef-horizontal-color.svg" alt="OpenSTEF" width="400"/>
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

**OpenSTEF** (Open Short-Term Energy Forecasting) is an open-source Python framework for creating accurate short-term load forecasts in the energy sector. It provides complete, model-agnostic pipelines covering data preprocessing, feature engineering, model training, probabilistic forecasting, evaluation, and post-processing. OpenSTEF is used in production at Alliander, generating forecasts for 10,000+ grid locations daily, and is designed to support use cases including congestion management, transport forecasting, and grid loss prediction. Learn more at the [LF Energy OpenSTEF project page](https://www.lfenergy.org/projects/openstef/).

---

## Repository Structure

OpenSTEF 4.0 is organised as a monorepo containing specialised packages that can be installed independently or together:

| Package | Purpose |
|---|---|
| **openstef** | Meta-package — installs all core components |
| **openstef-models** | ML models, feature engineering, and data processing |
| **openstef-beam** | Backtesting, Evaluation, Analysis, and Metrics (BEAM) |
| **openstef-core** | Shared types, dataset types, and base utilities |
| **openstef-compatibility** | OpenSTEF 3.x compatibility layer *(coming soon)* |
| **openstef-foundational-models** | Deep learning and foundational models *(coming soon)* |

---

## Installation

**Requirements:** Python 3.12+ · 64-bit OS (Windows, macOS, Linux)

```bash
# For most users
pip install openstef

# Core forecasting only
pip install openstef-models

# With all optional extras
pip install "openstef[all]"

# Using uv (recommended for development)
uv add openstef
```

For detailed instructions including Apple Silicon, GPU support, and troubleshooting, see the [Installation Guide](https://openstef.github.io/openstef/v4/user_guide/installation.html).

---

## Examples

Ready-to-run examples are in the [`examples/`](examples/) folder. See the [`examples/README.md`](examples/README.md) for an overview of all available examples, including benchmark runs against the Liander 2024 dataset and custom forecaster templates.

```bash
# Set up the full development environment
uv sync --all-extras --all-groups --all-packages

# Run the Liander 2024 benchmark
uv run python -m examples.benchmarks.custom_benchmark.run_liander2024_benchmark
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

If you use OpenSTEF in your research, please cite it using the metadata in [`CITATION.cff`](CITATION.cff). Most reference managers and GitHub's *Cite this repository* button can generate a citation automatically from that file.

---

## Contact

- **Slack:** [slack.lfenergy.org](https://slack.lfenergy.org/) — `#openstef` channel
- **Email:** [openstef@lfenergy.org](mailto:openstef@lfenergy.org)
- **Community meetings:** [LF Energy Confluence](https://lf-energy.atlassian.net/wiki/spaces/OS/pages/32278358/OpenSTEF+four-weekly+community+meeting)
- **Issue tracker:** [github.com/OpenSTEF/openstef/issues](https://github.com/OpenSTEF/openstef/issues)
- **Support guide:** [openstef.github.io/openstef/v4/project/support.html](https://openstef.github.io/openstef/v4/project/support.html)