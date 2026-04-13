I now have all the information needed to produce an accurate, complete README. Here it is:

<!--
SPDX-FileCopyrightText: 2017-2025 Contributors to the OpenSTEF project <openstef@lfenergy.org>

SPDX-License-Identifier: MPL-2.0
-->

<p align="center">
  <img src="https://raw.githubusercontent.com/OpenSTEF/openstef/main/docs/source/_static/logos/openstef-horizontal-color.svg" alt="OpenSTEF logo" width="400"/>
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

**OpenSTEF** (Open Short-Term Energy Forecasting) is an open-source Python framework for creating accurate short-term load forecasts in the energy sector. It provides complete machine learning pipelines covering data preprocessing, feature engineering, model training, forecasting, evaluation, and post-processing. OpenSTEF generates probabilistic forecasts with uncertainty bandwidths and includes built-in domain knowledge for energy-specific use cases such as congestion management, transport forecasting, and grid loss prediction. Learn more at the [OpenSTEF project homepage](https://www.lfenergy.org/projects/openstef/).

---

## Repository Structure

OpenSTEF 4.0 uses a monorepo workspace with the following packages:

| Package | Description |
|---|---|
| `openstef` | Meta-package — installs the core components |
| `openstef-core` | Core utilities, dataset types, shared types and base models |
| `openstef-models` | ML models, feature engineering, and data processing |
| `openstef-beam` | Backtesting, Evaluation, Analysis, and Metrics |
| `openstef-compatibility` | OpenSTEF 3.x compatibility layer *(coming soon)* |
| `openstef-foundational-models` | Deep learning and foundational models *(coming soon)* |

All packages are developed together; dependencies between them are automatically resolved via the workspace defined in `pyproject.toml`.

---

## How to Install

**Requirements:** Python 3.12+ · 64-bit OS (Windows, macOS, Linux)

```bash
# Recommended for most users
pip install openstef

# All optional components
pip install "openstef[all]"

# Individual packages
pip install openstef-core
pip install openstef-models
pip install openstef-beam
```

```bash
# Using uv (recommended for development)
uv add openstef

# Using conda
conda install -c conda-forge openstef
```

For platform-specific notes (Apple Silicon, GPU, WSL) and a full development setup, see the **[Installation Guide](https://openstef.github.io/openstef/v4/user_guide/installation.html)**.

---

## Examples

Hands-on examples and tutorials are available in the [`examples/`](examples/) folder. See the [`examples/README.md`](examples/README.md) for an overview of what is available.

Additional guided tutorials are published in the **[online documentation](https://openstef.github.io/openstef/v4/user_guide/tutorials.html)**.

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

If you use OpenSTEF in your research, please cite the project. The full citation details, BibTeX entry, and a downloadable `CITATION.cff` file are available on the **[Citing OpenSTEF](https://openstef.github.io/openstef/v4/project/citing.html)** page.

---

## Contact

- 💬 **Slack** — Join [LF Energy Slack](https://slack.lfenergy.org/) and find us in `#openstef`
- 📧 **Email** — [openstef@lfenergy.org](mailto:openstef@lfenergy.org)
- 🐛 **Issues** — [GitHub Issue Tracker](https://github.com/OpenSTEF/openstef/issues)
- 🤝 **Community meetings** — Four-weekly open meetings; details on the [LF Energy wiki](https://wiki.lfenergy.org/display/OS/Four-weekly+community+meeting)
- 📖 **Support page** — [openstef.github.io/openstef/v4/project/support.html](https://openstef.github.io/openstef/v4/project/support.html)