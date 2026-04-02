Based on the current README provided and following the structure plan exactly, here is the complete README.md for release/v4.0.0:

---

<!--
SPDX-FileCopyrightText: 2017-2025 Contributors to the OpenSTEF project <openstef@lfenergy.org>

SPDX-License-Identifier: MPL-2.0
-->

# OpenSTEF

[![Downloads](https://static.pepy.tech/badge/openstef)](https://pepy.tech/project/openstef)
[![Downloads](https://static.pepy.tech/badge/openstef/month)](https://pepy.tech/project/openstef)
[![CII Best Practices](https://bestpractices.coreinfrastructure.org/projects/5585/badge)](https://bestpractices.coreinfrastructure.org/projects/5585)

## What is OpenSTEF

**OpenSTEF** is a modular Python library for creating short-term forecasts in the energy sector. It provides machine learning models, feature engineering, and backtesting tools designed for operational forecasting of renewable energy, demand, and grid loads. **[Learn more at openstef.github.io](https://openstef.github.io/openstef/v4/)**.

## Brief Monorepo Overview

OpenSTEF 4.0 uses a monorepo structure with specialized packages: **openstef-models** for ML forecasting, **openstef-beam** for backtesting and evaluation, **openstef-core** for shared utilities, and a meta-package **openstef** that bundles core components. This modular design allows you to install only what you need.

## How to Install

**Requirements**: Python 3.12+ on a 64-bit operating system (Windows, macOS, Linux).

```bash
# Install the full OpenSTEF package
pip install openstef

# Or install specific components
pip install openstef-models  # Core forecasting only
pip install openstef-beam    # Backtesting and evaluation

# Using modern package managers
uv add openstef              # Recommended for development
conda install -c conda-forge openstef
```

**[Complete installation guide](https://openstef.github.io/openstef/v4/user_guide/installation.html)** with troubleshooting and advanced options.

## Examples

Explore practical examples in the **[examples/ folder](examples/)** to get started with forecasting workflows, model training, and backtesting. The examples folder includes its own README with an overview of available tutorials.

**[Quick Start Guide](https://openstef.github.io/openstef/v4/user_guide/quick_start.html)** provides a step-by-step introduction with real-world scenarios.

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

If you use OpenSTEF in your research or project, please cite it appropriately. Visit our **[documentation](https://openstef.github.io/openstef/v4/)** for BibTeX entries and DOI information.

## Contact

- **[Support Guide](https://openstef.github.io/openstef/v4/project/support.html)** — how to get help
- **[GitHub Discussions](https://github.com/OpenSTEF/openstef/discussions)** — community Q&A
- **[Issue Tracker](https://github.com/paula-passet/openstef_Sia/issues)** — bug reports and feature requests
- **[LF Energy OpenSTEF](https://www.lfenergy.org/projects/openstef/)** — project homepage