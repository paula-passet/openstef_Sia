I now have sufficient information from the knowledge base to generate the complete, accurate README. Let me compile it.

<!--
SPDX-FileCopyrightText: 2017-2025 Contributors to the OpenSTEF project <openstef@lfenergy.org>

SPDX-License-Identifier: MPL-2.0
-->

<p align="center">
  <img src="https://raw.githubusercontent.com/OpenSTEF/.github/main/profile/assets/openstef_logo_wide_colorful_bg.png" alt="OpenSTEF logo" width="400"/>
</p>

<p align="center">
  <a href="https://pepy.tech/project/openstef"><img src="https://static.pepy.tech/badge/openstef" alt="Downloads"/></a>
  <a href="https://pepy.tech/project/openstef"><img src="https://static.pepy.tech/badge/openstef/month" alt="Downloads per month"/></a>
  <a href="https://bestpractices.coreinfrastructure.org/projects/5585"><img src="https://bestpractices.coreinfrastructure.org/projects/5585/badge" alt="CII Best Practices"/></a>
  <a href="https://github.com/paula-passet/openstef_Sia/releases/tag/release/v4.0.0"><img src="https://img.shields.io/badge/version-4.0.0-blue" alt="Version 4.0.0"/></a>
  <a href="LICENSE.md"><img src="https://img.shields.io/badge/license-MPL--2.0-green" alt="License: MPL-2.0"/></a>
</p>

---

## What is OpenSTEF?

**OpenSTEF** (Open Short-Term Energy Forecasting) is an open-source Python framework for creating accurate short-term energy forecasts in the power grid domain. It provides complete, model-agnostic pipelines for data preprocessing, feature engineering, model training, probabilistic forecasting, evaluation, and post-processing. OpenSTEF is designed for use cases including congestion management, transport forecasts, EV charging capacity estimation, and grid loss prediction. For more information, visit the [OpenSTEF project page](https://www.lfenergy.org/projects/openstef/).

---

## Repository Structure

OpenSTEF 4.0 is organised as a **modular monorepo**. Each sub-package is self-contained and can be installed independently:

| Package | Purpose |
|---|---|
| **`openstef`** | Meta-package — installs the full framework |
| **`openstef-core`** | Data types, interfaces, base classes, and shared utilities |
| **`openstef-models`** | Forecasting models, feature engineering, and data preprocessing |
| **`openstef-meta`** | Modern ensemble and advanced model architectures |
| **`openstef-beam`** | Backtesting, Evaluation, Analysis, and Metrics (BEAM) |

---

## Installation

**Requirements:** Python `>=3.12,<4.0` · 64-bit OS (Windows, macOS, Linux)

```bash
# Full framework (recommended)
pip install openstef

# Individual packages
pip install openstef-core
pip install openstef-models
pip install openstef-beam

# Using uv (recommended for development)
uv add openstef
```

For development, clone the repository and sync all dependencies:

```bash
git clone https://github.com/paula-passet/openstef_Sia.git
cd openstef_Sia
uv sync --dev
```

---

## Examples

The [`examples/`](examples/) directory contains runnable notebooks and scripts covering common use cases, including:

- Configuring a complete forecasting pipeline
- Running the Liander 2024 energy forecasting benchmark
- Comparing benchmark results across model runs

Before running any example, install all dependencies:

```bash
uv sync --all-extras --all-groups --all-packages
```

See [`examples/README.md`](examples/README.md) for a full overview of available examples.

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

If you use OpenSTEF in your research, please cite it. Citation metadata is provided in [`CITATION.cff`](CITATION.cff) at the root of this repository. A BibTeX entry can be generated from that file, or refer to the [OpenSTEF documentation](https://openstef.github.io/openstef/v4/) for the recommended citation format.

---

## Contact

| Channel | Link |
|---|---|
| **Slack** | [lfenergy.slack.com](https://slack.lfenergy.org/) |
| **Email** | [openstef@lfenergy.org](mailto:openstef@lfenergy.org) |
| **Community meeting** | [Four-weekly meeting notes](https://lf-energy.atlassian.net/wiki/spaces/OS/pages/32278358/OpenSTEF+four-weekly+community+meeting) |
| **Issue tracker** | [GitHub Issues](https://github.com/OpenSTEF/openstef/issues) |
| **Project homepage** | [LF Energy — OpenSTEF](https://www.lfenergy.org/projects/openstef/) |