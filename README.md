I now have all the information needed to produce the complete README. Here it is:

---

<p align="center">
  <img src="https://raw.githubusercontent.com/OpenSTEF/.github/main/profile/assets/openstef-horizontal-color.svg" alt="OpenSTEF" width="400"/>
</p>

<p align="center">
  <a href="https://github.com/paula-passet/openstef_Sia/actions"><img src="https://github.com/paula-passet/openstef_Sia/actions/workflows/ci.yml/badge.svg" alt="Build Status"/></a>
  <a href="https://github.com/paula-passet/openstef_Sia/blob/main/LICENSE"><img src="https://img.shields.io/badge/License-MPL%202.0-brightgreen.svg" alt="License: MPL-2.0"/></a>
  <a href="https://github.com/paula-passet/openstef_Sia/releases/tag/v4.0.1"><img src="https://img.shields.io/badge/version-v4.0.1-blue.svg" alt="Version: v4.0.1"/></a>
  <a href="https://pypi.org/project/openstef/"><img src="https://img.shields.io/pypi/pyversions/openstef" alt="Python Versions"/></a>
  <a href="https://www.lfenergy.org/projects/openstef/"><img src="https://img.shields.io/badge/LF%20Energy-OpenSTEF-orange.svg" alt="LF Energy"/></a>
</p>

---

## What is OpenSTEF?

**OpenSTEF** (Open Short-Term Energy Forecasting) is an open-source, model-agnostic Python framework for accurate short-term energy load forecasting — predicting load hours to days ahead. It provides complete machine learning pipelines covering data preprocessing, feature engineering, model training, forecasting, evaluation, and post-processing, and produces probabilistic forecasts with uncertainty bandwidths rather than single-point predictions. OpenSTEF is designed for use cases including congestion management, transport forecasts, EV charging capacity estimation, and grid loss prediction. Learn more at the [LF Energy OpenSTEF project page](https://www.lfenergy.org/projects/openstef/).

---

## Repository Structure

This repository is organised as a **modular monorepo** containing four self-contained packages:

| Package | Description |
|---|---|
| [`openstef-core`](packages/openstef-core/) | Data types, interfaces, base classes, and shared utilities — the foundation for all other packages |
| [`openstef-models`](packages/openstef-models/) | Forecasting models, preprocessing pipelines, energy-specific feature engineering, and presets |
| [`openstef-meta`](packages/openstef-meta/) | Meta-learning and ensemble model architectures |
| [`openstef-beam`](packages/openstef-beam/) | Backtesting, Evaluation, Analysis, and Metrics (BEAM) — regression testing and forecast validation |

The top-level `openstef` meta-package installs all four packages together.

---

## Installation

**Requirements:** Python ≥ 3.12, < 4.0

Install the complete framework:

```bash
pip install openstef
```

Or install individual packages as needed:

```bash
# Core data types and interfaces
pip install openstef-core

# Forecasting models
pip install openstef-models

# Meta / ensemble models
pip install openstef-meta

# Backtesting, evaluation, and metrics
pip install openstef-beam

# openstef-beam with all optional extras (e.g. S3 support)
pip install openstef-beam[all]

# openstef-models with LightGBM support
pip install openstef-models[lgbm]

# openstef-models with XGBoost (CPU)
pip install openstef-models[xgb-cpu]
```

Verify your installation:

```python
import openstef_core
print(openstef_core.__version__)

import openstef_beam
print(openstef_beam.__version__)
```

---

## Examples

Ready-to-run examples are available in the [`examples/`](examples/) folder. See the [examples README](examples/README.md) for an overview of available notebooks and scripts covering common forecasting workflows.

---

## License

This project is licensed under the **Mozilla Public License 2.0 (MPL-2.0)**. See the [`LICENSE`](LICENSE) file for full terms.

```
SPDX-License-Identifier: MPL-2.0
SPDX-FileCopyrightText: 2017-2025 Contributors to the OpenSTEF project <openstef@lfenergy.org>
```

---

## Contributing

Contributions are welcome! Please refer to the contributing guidelines and code of conduct in the [OpenSTEF `.github` repository](https://github.com/OpenSTEF/.github) before opening a pull request. The project uses `uv` and `ruff` for development tooling and `mypy` for type checking — details are in the contributing guide.

---

## Citations

If you use OpenSTEF in your research or work, please cite the project:

```bibtex
@software{openstef,
  author       = {Contributors to the OpenSTEF project},
  title        = {{OpenSTEF}: Open Short-Term Energy Forecasting},
  version      = {v4.0.1},
  year         = {2025},
  url          = {https://github.com/paula-passet/openstef_Sia},
  license      = {MPL-2.0}
}
```

For the upstream canonical project, see [github.com/OpenSTEF/openstef](https://github.com/OpenSTEF/openstef).

---

## Contact

- **Slack:** [lfenergy.slack.com](https://slack.lfenergy.org/) — join the `#openstef` channel
- **Email:** [openstef@lfenergy.org](mailto:openstef@lfenergy.org)
- **Community meetings:** [Four-weekly community call](https://lf-energy.atlassian.net/wiki/spaces/OS/pages/32278358/OpenSTEF+four-weekly+community+meeting)
- **Bug reports & feature requests:** [GitHub Issues](https://github.com/paula-passet/openstef_Sia/issues)