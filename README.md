I now have all the information needed to produce a complete, accurate README. Let me compile it.

<!--
SPDX-FileCopyrightText: 2017-2025 Contributors to the OpenSTEF project <openstef@lfenergy.org>

SPDX-License-Identifier: MPL-2.0
-->

<p align="center">
  <img src="docs/logos/openstef-horizontal-color.svg" alt="OpenSTEF logo" width="400"/>
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

**OpenSTEF** (Open Short-Term Energy Forecasting) is an open-source Python framework for creating accurate short-term load forecasts in the energy sector. It provides complete, model-agnostic pipelines covering data preprocessing, feature engineering, model training, probabilistic forecasting, evaluation, and post-processing. OpenSTEF is designed for use cases including congestion management, transport forecasts, grid loss prediction, and EV charging capacity estimation. Visit the [OpenSTEF website](https://www.lfenergy.org/projects/openstef/) for more information.

---

## Monorepo Overview

OpenSTEF v4.0.0 is structured as a modular monorepo. Each package is self-contained and can be installed independently:

| Package | Purpose |
|---|---|
| **openstef** | Meta-package — installs the full framework (`openstef-core`, `openstef-models`, `openstef-beam`, `openstef-meta`) |
| **openstef-core** | Core data types, interfaces, shared exceptions, and base classes used by all other packages |
| **openstef-models** | Forecasting models, feature engineering, data preprocessing pipelines, and explainability |
| **openstef-beam** | Backtesting, Evaluation, Analysis, and Metrics (BEAM) |
| **openstef-meta** | Meta/ensemble models built on top of `openstef-models` |

---

## How to Install

**Requirements:** Python ≥ 3.12, < 4.0 · 64-bit OS (Windows, macOS, Linux)

```bash
# Install the full framework
pip install openstef

# Install individual packages
pip install openstef-core
pip install openstef-models
pip install openstef-beam
pip install openstef-meta

# Install with optional extras (e.g. LightGBM support)
pip install "openstef-models[lgbm]"

# Install everything including all optional extras
pip install "openstef-beam[all]"

# Using uv (recommended for development)
uv add openstef
```

To set up a local development environment from source:

```bash
git clone https://github.com/OpenSTEF/openstef.git -b "release/v4.0.0"
cd openstef
uv sync --all-extras --all-groups --all-packages
```

---

## Examples

Ready-to-run examples are in the [`examples/`](examples/) folder. See the [`examples/README.md`](examples/README.md) for a full overview of available examples, including:

- **Benchmark examples** — run the built-in [Liander 2024 Energy Forecasting Benchmark](examples/benchmarks/custom_benchmark/) against your own models
- **Custom benchmarks** — bring your own data and pipeline configuration
- **Forecast evaluation** — evaluate pre-existing forecasts without re-running backtesting

Quick start with the built-in benchmark:

```bash
# After cloning and running `uv sync --all-extras --all-groups --all-packages`
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

If you use OpenSTEF in your research, please cite the project. Citation metadata is maintained in [`CITATION.cff`](CITATION.cff) at the root of this repository. Most reference managers and GitHub's *Cite this repository* button can import it directly.

---

## Contact

- **Slack:** [LF Energy Slack](https://slack.lfenergy.org/) — `#openstef` channel
- **Email:** [openstef@lfenergy.org](mailto:openstef@lfenergy.org)
- **Community meetings:** [OpenSTEF four-weekly community meeting](https://lf-energy.atlassian.net/wiki/spaces/OS/pages/32278358/OpenSTEF+four-weekly+community+meeting)
- **Issue tracker:** [GitHub Issues](https://github.com/OpenSTEF/openstef/issues)
- **Project homepage:** [LF Energy — OpenSTEF](https://www.lfenergy.org/projects/openstef/)