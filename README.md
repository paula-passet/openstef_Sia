Now I have all the information needed. Let me generate the README.

<!--
SPDX-FileCopyrightText: 2017-2025 Contributors to the OpenSTEF project <openstef@lfenergy.org>

SPDX-License-Identifier: MPL-2.0
-->

<p align="center">
  <a href="https://www.lfenergy.org/projects/openstef/">
    <img src="docs/source/_static/openstef-horizontal-color.svg" alt="OpenSTEF logo" width="400">
  </a>
</p>

<!-- Badges -->

<p align="center">
  <a href="https://pepy.tech/project/openstef"><img src="https://static.pepy.tech/badge/openstef" alt="Downloads"></a>
  <a href="https://pepy.tech/project/openstef"><img src="https://static.pepy.tech/badge/openstef/month" alt="Downloads/month"></a>
  <a href="https://bestpractices.coreinfrastructure.org/projects/5585"><img src="https://bestpractices.coreinfrastructure.org/projects/5585/badge" alt="CII Best Practices"></a>
  <a href="https://github.com/paula-passet/openstef_Sia/releases/tag/release/v4.0.0"><img src="https://img.shields.io/badge/release-v4.0.0-blue" alt="Release v4.0.0"></a>
  <a href="LICENSE.md"><img src="https://img.shields.io/badge/license-MPL--2.0-brightgreen" alt="License: MPL-2.0"></a>
</p>

## What is OpenSTEF

**OpenSTEF** is a modular Python library for creating short-term forecasts in the energy sector. Version 4.0 introduces a complete architectural refactor with enhanced modularity, full type safety, and modern development practices. Install only the components you need, from core forecasting models to backtesting and evaluation tools. Learn more at the [LF Energy OpenSTEF homepage](https://www.lfenergy.org/projects/openstef/).

## Monorepo Overview

OpenSTEF 4.0 uses a monorepo workspace structure with specialized packages:

| Package | Purpose | Install |
|---------|---------|---------|
| **openstef** | Meta-package with core components | `pip install openstef` |
| **openstef-models** | ML models, feature engineering, data processing | `pip install openstef-models` |
| **openstef-beam** | Backtesting, Evaluation, Analysis, Metrics | `pip install openstef-beam` |
| **openstef-core** | Core utilities, dataset types, shared types and base models | `pip install openstef-core` |

Source code lives under `packages/openstef-models/`, `packages/openstef-beam/`, and `packages/openstef-core/`. The workspace is managed via `uv` with a shared `pyproject.toml`.

## How to Install

**Requirements:** Python 3.12+ · 64-bit OS (Windows, macOS, Linux)

```bash
# For most users
pip install openstef

# With all optional packages
pip install "openstef[all]"

# Using uv (recommended for development)
uv add openstef
```

For detailed options—including per-package installation, conda support, and development setup—see the [Installation Guide](https://openstef.github.io/openstef/v4/user_guide/installation.html).

## Examples

Explore ready-to-run examples in the [`examples/`](examples/) folder. The folder contains its own `README.md` with an overview of available examples and tutorials.

For guided walkthroughs, see the [Quick Start Guide](https://openstef.github.io/openstef/v4/user_guide/quick_start.html) and [Tutorials](https://openstef.github.io/openstef/v4/user_guide/tutorials.html).

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

If you use OpenSTEF in your research, please cite the project using DOI [10.5281/zenodo.15316405](https://doi.org/10.5281/zenodo.15316405):

```bibtex
@software{openstefopenstef,
  title   = {OpenSTEF/openstef},
  author  = {Kreuwel, Frank and van Es, Daan and van Doorn, Jan Maarten
             and Pleiter, Bart and Stoel, Willem Frederik
             and van den Bogaard, Jonas and Fortin, Maxime
             and de Smet, Clara and Dmitriev, Egor
             and Schilders, Lars and Harmsen, A. W.},
  doi     = {10.5281/zenodo.15316405},
  url     = {https://github.com/OpenSTEF/openstef},
}
```

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.15316405.svg)](https://doi.org/10.5281/zenodo.15316405)

## Contact

- **[Support Guide](https://openstef.github.io/openstef/v4/project/support.html)** — how to get help, Slack channel, community meetings
- **[GitHub Discussions](https://github.com/OpenSTEF/openstef/discussions)** — community Q&A
- **[Issue Tracker](https://github.com/OpenSTEF/openstef/issues)** — bug reports and feature requests
- **Email:** [openstef@lfenergy.org](mailto:openstef@lfenergy.org)