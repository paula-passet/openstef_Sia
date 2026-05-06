<p align="center">
  <img src="https://raw.githubusercontent.com/OpenSTEF/.github/main/profile/assets/openstef_logo_wide_colorful_bg.svg" alt="OpenSTEF logo" width="400"/>
</p>

<p align="center">
  <a href="https://github.com/paula-passet/openstef_Sia/releases/tag/v4.0.1"><img src="https://img.shields.io/badge/release-v4.0.1-blue" alt="Release v4.0.1"/></a>
  <a href="https://pypi.org/project/openstef/"><img src="https://img.shields.io/pypi/v/openstef" alt="PyPI version"/></a>
  <a href="https://pypi.org/project/openstef/"><img src="https://img.shields.io/pypi/pyversions/openstef" alt="Python versions"/></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MPL--2.0-brightgreen" alt="License: MPL-2.0"/></a>
  <a href="https://github.com/paula-passet/openstef_Sia/actions"><img src="https://img.shields.io/github/actions/workflow/status/paula-passet/openstef_Sia/ci.yml?branch=main&label=build" alt="Build status"/></a>
  <a href="https://slack.lfenergy.org/"><img src="https://img.shields.io/badge/slack-lfenergy-purple?logo=slack" alt="Slack"/></a>
</p>

---

## What is OpenSTEF?

**OpenSTEF** (Open Short-Term Energy Forecasting) is an open-source Python framework for accurate short-term energy load forecasting — predicting load hours to days ahead. It provides complete, model-agnostic machine learning pipelines covering data preprocessing, feature engineering, model training, probabilistic forecasting, evaluation, and post-processing. OpenSTEF includes built-in domain knowledge for energy use cases such as congestion management, transport forecasts, and grid loss prediction, and generates probabilistic forecasts with uncertainty bandwidths rather than single-point predictions. For a full overview, visit the [OpenSTEF documentation site](https://openstef.github.io/openstef/).

---

## Repository Structure

This repository is a **modular monorepo** composed of four self-contained packages:

| Package | Description |
|---|---|
| [`openstef-core`](packages/openstef-core/) | Data types, interfaces, base classes, and shared utilities — the foundation for all other packages |
| [`openstef-models`](packages/openstef-models/) | Forecasting models, preprocessing pipelines, energy-specific transforms, explainability, and presets |
| [`openstef-meta`](packages/openstef-meta/) | Meta-learning and ensemble model architectures |
| [`openstef-beam`](packages/openstef-beam/) | Backtesting, Evaluation, Analysis, and Metrics (BEAM) — regression testing and benchmarking |

The top-level `openstef` package is a convenience meta-package that installs all four.

---

## How to Install

**Requirements:** Python ≥ 3.12, < 4.0

### Install everything (recommended)

```bash
pip install openstef
```

### Install individual packages

```bash
# Core functionality only
pip install openstef-core

# Forecasting models
pip install openstef-models

# Meta / ensemble models
pip install openstef-meta

# Backtesting, evaluation, and metrics
pip install openstef-beam
```

### Install with optional extras

```bash
# openstef-models with LightGBM support
pip install openstef-models[lgbm]

# openstef-models with XGBoost (CPU)
pip install openstef-models[xgb-cpu]

# openstef-beam with all extras (baselines + S3 support)
pip install openstef-beam[all]
```

### Verify your installation

```python
import openstef_core
print(openstef_core.__version__)

import openstef_beam
print(openstef_beam.__version__)
```

---

## Examples

Runnable examples and notebooks are available in the [`examples/`](examples/) folder. See the [`examples/README.md`](examples/README.md) for a full overview of available examples and how to run them.

---

## License

This project is licensed under the **Mozilla Public License 2.0 (MPL-2.0)**. See the [`LICENSE`](LICENSE) file for the full text.

```
SPDX-License-Identifier: MPL-2.0
SPDX-FileCopyrightText: 2017-2025 Contributors to the OpenSTEF project <openstef@lfenergy.org>
```

---

## Contributing

Contributions are welcome! Please refer to the contributing guidelines and code of conduct in the [OpenSTEF `.github` repository](https://github.com/OpenSTEF/.github) before opening a pull request. The project uses [UV](https://github.com/astral-sh/uv) and [Ruff](https://github.com/astral-sh/ruff) for development tooling, [mypy](https://mypy-lang.org/) for type checking, and `openstef-beam` for regression benchmarking. Look for issues labelled **good first issue** on the [issue tracker](https://github.com/OpenSTEF/openstef/issues) to get started.

---

## Citations

If you use OpenSTEF in your research, please cite it using the metadata in [`CITATION.cff`](CITATION.cff). A BibTeX entry can be generated automatically from that file, or you can use the **Cite this repository** button on the GitHub repository page.

---

## Contact

For questions, support, or community discussion:

- **Slack:** [lfenergy.slack.org](https://slack.lfenergy.org/) — join the `#openstef` channel
- **Email:** [openstef@lfenergy.org](mailto:openstef@lfenergy.org)
- **Community meetings:** [four-weekly community call](https://lf-energy.atlassian.net/wiki/spaces/OS/pages/32278358/OpenSTEF+four-weekly+community+meeting)