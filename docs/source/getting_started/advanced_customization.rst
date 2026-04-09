Advanced Customization
======================

OpenSTEF provides multiple extension points for power users who need to customize the forecasting pipeline beyond the standard configuration options. This guide shows you how to implement custom data preparation logic, build custom feature engineering transforms, and create custom workflow orchestrations.

Before diving into customization, make sure you're comfortable with the basics covered in :doc:`quickstart` and :doc:`first_forecast`.

Custom Feature Engineering
---------------------------

The most common customization need is adding domain-specific features to your forecasting pipeline. OpenSTEF uses a transform-based architecture where you can plug in custom feature engineering logic.

Creating a Custom Transform
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Custom transforms inherit from ``TimeSeriesTransform`` and implement two key methods: ``transform()`` to apply the transformation, and ``features_added()`` to declare which columns are created.

.. code-block:: python

    from openstef_core.datasets import TimeSeriesDataset
    from openstef_core.transforms import TimeSeriesTransform
    import pandas as pd
    
    class HolidayFeatureAdder(TimeSeriesTransform):
        """Add binary holiday indicator features."""
        
        def __init__(self, country_code: str = "NL"):
            self.country_code = country_code
            self._holiday_dates = None
        
        @property
        def is_fitted(self) -> bool:
            """Transform is fitted after seeing training data."""
            return self._holiday_dates is not None
        
        def fit(self, data: TimeSeriesDataset) -> None:
            """Learn holiday dates from the training period."""
            # In practice, you'd load from a holiday calendar library
            self._holiday_dates = self._load_holidays(
                data.index.min(), 
                data.index.max()
            )
        
        def transform(self, data: TimeSeriesDataset) -> TimeSeriesDataset:
            """Add holiday features to the dataset."""
            df = data.data.copy()
            
            # Add binary holiday indicator
            df['is_holiday'] = df.index.date.isin(self._holiday_dates).astype(int)
            
            # Add "day before holiday" indicator
            df['is_pre_holiday'] = (
                (df.index + pd.Timedelta(days=1))
                .date.isin(self._holiday_dates)
                .astype(int)
            )
            
            return TimeSeriesDataset(df, data.sample_interval)
        
        def features_added(self) -> list[str]:
            """Declare which features this transform creates."""
            return ['is_holiday', 'is_pre_holiday']
        
        def _load_holidays(self, start, end):
            # Simplified - use a proper holiday library in production
            return {pd.Timestamp('2024-12-25').date()}

Stateless transforms (those that don't need to learn from training data) can simply return ``True`` from ``is_fitted`` and leave ``fit()`` as a no-op.

Integrating Custom Transforms into Pipelines
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Once you've created a custom transform, add it to a model's preprocessing pipeline using ``TransformPipeline``:

.. code-block:: python

    from openstef_core.transforms import TransformPipeline
    from openstef_models.models import ForecastingModel
    from openstef_models.models.regressors import XGBQuantileOpenstfRegressor
    
    # Create your custom transform
    holiday_transform = HolidayFeatureAdder(country_code="NL")
    
    # Build a preprocessing pipeline with built-in and custom transforms
    preprocessing = TransformPipeline[TimeSeriesDataset](
        transforms=[
            holiday_transform,
            # Add other transforms as needed
        ]
    )
    
    # Create a model with the custom preprocessing
    model = ForecastingModel(
        model=XGBQuantileOpenstfRegressor(),
        preprocessing=preprocessing,
        target_column="load"
    )
    
    # Use normally - the custom features are automatically applied
    model.fit(train_data)
    forecast = model.predict(test_data)

The pipeline applies transforms sequentially, with each transform receiving the output of the previous one. All transforms are fitted during ``model.fit()`` and applied during ``model.predict()``.

Custom Data Preparation
------------------------

For more complex preprocessing needs that go beyond feature engineering—such as data validation, outlier handling, or multi-source data fusion—you can customize the data preparation stage.

Preprocessing vs. Postprocessing
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

OpenSTEF models support two transform pipelines:

- **Preprocessing**: Applied before model training/prediction. Use for feature engineering, normalization, and data cleaning.
- **Postprocessing**: Applied after model prediction. Use for forecast adjustments, unit conversions, or constraint enforcement.

Here's an example of a custom postprocessing transform that enforces physical constraints:

.. code-block:: python

    class CapacityConstraint(TimeSeriesTransform):
        """Clip forecasts to physical capacity limits."""
        
        def __init__(self, min_capacity: float = 0.0, max_capacity: float = None):
            self.min_capacity = min_capacity
            self.max_capacity = max_capacity
        
        @property
        def is_fitted(self) -> bool:
            return True  # Stateless transform
        
        def transform(self, data: TimeSeriesDataset) -> TimeSeriesDataset:
            """Clip all numeric columns to capacity range."""
            df = data.data.copy()
            numeric_cols = df.select_dtypes(include=['number']).columns
            
            for col in numeric_cols:
                df[col] = df[col].clip(
                    lower=self.min_capacity,
                    upper=self.max_capacity
                )
            
            return TimeSeriesDataset(df, data.sample_interval)
        
        def features_added(self) -> list[str]:
            return []  # Modifies existing features, doesn't add new ones
    
    # Apply as postprocessing
    model = ForecastingModel(
        model=XGBQuantileOpenstfRegressor(),
        postprocessing=TransformPipeline[TimeSeriesDataset](
            transforms=[CapacityConstraint(min_capacity=0, max_capacity=1000)]
        ),
        target_column="load"
    )

Model-Specific Preprocessing
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

When working with ensemble models, you may need different preprocessing for different base models. OpenSTEF supports this through model-specific preprocessing pipelines:

.. code-block:: python

    from openstef_models.models import EnsembleForecastingModel
    
    # Common preprocessing applied to all models
    common_preprocessing = TransformPipeline[TimeSeriesDataset](
        transforms=[
            HolidayFeatureAdder(),
            # Other common transforms
        ]
    )
    
    # Model-specific preprocessing applied after common preprocessing
    model_specific = {
        "xgb_model": TransformPipeline[TimeSeriesDataset](
            transforms=[
                # XGBoost-specific feature engineering
            ]
        ),
        "linear_model": TransformPipeline[TimeSeriesDataset](
            transforms=[
                # Linear model needs different features
            ]
        ),
    }
    
    ensemble = EnsembleForecastingModel(
        models={"xgb_model": xgb_model, "linear_model": linear_model},
        preprocessing=common_preprocessing,
        model_specific_preprocessing=model_specific,
        combiner=combiner_model
    )

Custom Workflow Orchestration
------------------------------

For production systems that need custom lifecycle management, monitoring, or persistence logic, you can create custom workflows using the callback system.

Workflow Callbacks
^^^^^^^^^^^^^^^^^^

Callbacks provide hooks into the workflow lifecycle without modifying the core forecasting logic. This is useful for logging, metrics collection, model validation, and integration with external systems.

.. code-block:: python

    from openstef_models.workflows import CustomForecastingWorkflow, ForecastingCallback
    from openstef_models.mixins.callbacks import WorkflowContext
    from openstef_core.datasets import TimeSeriesDataset, ForecastDataset
    import logging
    
    class MetricsCallback(ForecastingCallback):
        """Collect and report metrics during workflow execution."""
        
        def __init__(self, metrics_client):
            self.metrics_client = metrics_client
            self.logger = logging.getLogger(__name__)
        
        def on_fit_start(
            self, 
            context: WorkflowContext, 
            data: TimeSeriesDataset
        ) -> None:
            """Called before model training starts."""
            self.logger.info(
                f"Training {context.workflow.model_id} with {len(data.data)} samples"
            )
            self.metrics_client.gauge(
                'training.data_size', 
                len(data.data),
                tags={'model': context.workflow.model_id}
            )
        
        def on_fit_end(
            self, 
            context: WorkflowContext, 
            result
        ) -> None:
            """Called after model training completes."""
            self.logger.info(f"Training completed for {context.workflow.model_id}")
            self.metrics_client.increment(
                'training.completed',
                tags={'model': context.workflow.model_id}
            )
        
        def on_predict_end(
            self,
            context: WorkflowContext,
            data: TimeSeriesDataset,
            result: ForecastDataset
        ) -> None:
            """Called after prediction completes."""
            forecast_count = len(result.data)
            self.metrics_client.gauge(
                'forecast.count',
                forecast_count,
                tags={'model': context.workflow.model_id}
            )

Use callbacks by passing them to the workflow constructor:

.. code-block:: python

    from openstef_models.workflows import CustomForecastingWorkflow
    
    # Create workflow with callbacks
    workflow = CustomForecastingWorkflow(
        model=model,
        callbacks=[
            MetricsCallback(metrics_client),
            # Add multiple callbacks as needed
        ]
    )
    
    # Use workflow normally - callbacks are invoked automatically
    workflow.fit(train_data)
    forecasts = workflow.predict(test_data)

All callback methods have default no-op implementations, so you only need to override the specific lifecycle events you care about.

Combining Custom Components
----------------------------

The real power of OpenSTEF's customization system comes from combining multiple extension points. Here's a complete example that brings together custom transforms, custom preprocessing, and custom workflows:

.. code-block:: python

    from openstef_models.models import ForecastingModel
    from openstef_models.workflows import CustomForecastingWorkflow
    from openstef_core.transforms import TransformPipeline
    
    # 1. Custom feature engineering
    preprocessing = TransformPipeline[TimeSeriesDataset](
        transforms=[
            HolidayFeatureAdder(country_code="NL"),
            # Add more custom transforms
        ]
    )
    
    # 2. Custom postprocessing
    postprocessing = TransformPipeline[TimeSeriesDataset](
        transforms=[
            CapacityConstraint(min_capacity=0, max_capacity=1000)
        ]
    )
    
    # 3. Build model with custom pipelines
    model = ForecastingModel(
        model=XGBQuantileOpenstfRegressor(),
        preprocessing=preprocessing,
        postprocessing=postprocessing,
        target_column="load"
    )
    
    # 4. Wrap in workflow with custom callbacks
    workflow = CustomForecastingWorkflow(
        model=model,
        callbacks=[MetricsCallback(metrics_client)]
    )
    
    # 5. Use the fully customized system
    workflow.fit(train_data)
    forecasts = workflow.predict(test_data)

This architecture keeps concerns separated: feature engineering logic lives in transforms, business logic lives in callbacks, and the core forecasting logic remains unchanged.

Best Practices
--------------

When customizing OpenSTEF, follow these guidelines:

- **Keep transforms focused**: Each transform should do one thing well. Compose multiple simple transforms rather than creating complex monolithic ones.

- **Declare features explicitly**: Always implement ``features_added()`` accurately. This helps with debugging and enables automatic feature tracking.

- **Handle missing data gracefully**: Your transforms will encounter missing values, irregular timestamps, and edge cases. Add appropriate validation and error handling.

- **Test transforms independently**: Write unit tests for your custom transforms before integrating them into pipelines.

- **Use callbacks for side effects**: Keep transforms pure (no I/O, no logging to files). Use callbacks for side effects like metrics, logging, and persistence.

- **Document your customizations**: Custom components should include docstrings explaining what they do and why they're needed.

Next Steps
----------

Now that you understand OpenSTEF's extension points, you might want to:

- Learn about :doc:`backtesting` to evaluate your custom models
- Explore the built-in transforms in the API documentation to see what's already available
- Review the examples directory for more complex customization patterns

For questions about customization or to share your custom components with the community, visit the OpenSTEF GitHub repository.