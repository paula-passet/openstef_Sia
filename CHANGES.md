# CHANGES.md

## [aa8c516](https://github.com/paula-passet/openstef_Sia/commit/aa8c516b0a64a7e6862a9d5e3375ecd8e74fc97f) - Forecast Analysis Refactoring

### Breaking Changes
- **Removed** `breakdown_forecast()` function from `openstef.metrics.breakdown_forecast` module
- **Added** `summarize_forecast()` function in new `openstef.metrics.forecast_summary` module

### Migration Guide
Replace calls to `breakdown_forecast()` with `summarize_forecast()`:

```python
# Old
from openstef.metrics.breakdown_forecast import breakdown_forecast

# New  
from openstef.metrics.forecast_summary import summarize_forecast
```

This change consolidates forecast analysis functionality under a clearer API with improved naming conventions.