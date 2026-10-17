from pydantic import BaseModel, Field


class FeatureConfig(BaseModel):
    """Configuration for global backward-looking feature engineering."""

    lags: list[int] = Field(default_factory=list, description="List of lag offsets.")
    rolling_windows: list[int] = Field(
        default_factory=list, description="List of backward-looking rolling window sizes."
    )
    include_day_of_week: bool = Field(default=False)
    include_month: bool = Field(default=False)
    include_year: bool = Field(default=False)


class SplitConfig(BaseModel):
    """Configuration for temporal splitting."""

    train_ratio: float = Field(default=0.7, description="Proportion of data for training.")
    val_ratio: float = Field(default=0.15, description="Proportion of data for validation.")
    test_ratio: float = Field(default=0.15, description="Proportion of data for testing.")


class ForecastConfig(BaseModel):
    """Overall configuration for a forecasting pipeline run."""

    dataset_name: str
    target_column: str
    features: FeatureConfig
    split: SplitConfig
    baseline_model_type: str = Field(default="naive")
    baseline_model_kwargs: dict = Field(default_factory=dict)

    # Chunk 2.2 Additions
    horizon: int = Field(default=1, description="Forecast horizon in steps.")
    walk_forward_origins: int = Field(
        default=1, description="Number of rolling origins for evaluation."
    )
    high_demand_quantile: float | None = Field(
        default=None, description="Quantile threshold for high-demand evaluation (e.g. 0.90)."
    )

    # Chunk 2.3 Additions
    model_type: str = Field(
        default="baseline", description="Category of model: baseline, arima, prophet, lstm"
    )
    arima_order: tuple[int, int, int] = Field(default=(1, 0, 0), description="(p, d, q) for ARIMA")
    arima_seasonal_order: tuple[int, int, int, int] = Field(
        default=(0, 0, 0, 0), description="(P, D, Q, s) for SARIMA"
    )
    prophet_kwargs: dict = Field(
        default_factory=dict, description="Configuration overrides for Prophet"
    )

    # Chunk 2.4 Additions (Deep Learning / LSTM)
    lstm_hidden_dim: int = Field(default=64, description="Hidden state dimension for LSTM units.")
    lstm_num_layers: int = Field(default=2, description="Number of stacked LSTM layers.")
    lstm_dropout: float = Field(default=0.2, description="Dropout probability for regularization.")
    lstm_epochs: int = Field(default=25, description="Training epochs for LSTM optimizer.")
    lstm_batch_size: int = Field(
        default=32, description="Batch size for LSTM mini-batch gradient descent."
    )
    lstm_learning_rate: float = Field(default=0.005, description="Learning rate for AdamW optimizer.")
    lstm_sequence_length: int = Field(
        default=14, description="Sliding lookback sequence window length."
    )
    lstm_mc_samples: int = Field(
        default=20, description="Monte Carlo dropout forward passes for CI bounds."
    )

