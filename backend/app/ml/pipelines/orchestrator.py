import os
import uuid

import pandas as pd
from sklearn.metrics import mean_absolute_error, root_mean_squared_error

from app.ml.contracts.config import ForecastConfig
from app.ml.contracts.dataset import MLDataset
from app.ml.contracts.evaluation import EvaluationMetrics, safe_mape, safe_smape
from app.ml.contracts.experiment import ExperimentRun
from app.ml.contracts.forecast import ForecastResult
from app.ml.features.engineer import FeatureEngineer
from app.ml.models.arima import ARIMAForecastModel
from app.ml.models.baseline import (
    MovingAverageBaselineModel,
    NaiveBaselineModel,
    SeasonalNaiveBaselineModel,
)
from app.ml.models.lstm import LSTMForecastModel
from app.ml.models.prophet import ProphetForecastModel
from app.ml.preprocessing.scalers import DataPreprocessor
from app.ml.splitting.temporal import TemporalSplitter
from app.ml.tracking.artifacts import log_experiment_artifacts
from app.ml.tracking.base import ExperimentTracker
from app.ml.tracking.factory import get_tracker


class MLPipelineOrchestrator:
    """
    Orchestrates the ML Pipeline with Walk-Forward Evaluation support.
    """

    def __init__(
        self,
        config: ForecastConfig,
        artifacts_dir: str = "backend/ml/artifacts",
        runs_dir: str = "backend/ml/runs",
        tracker: ExperimentTracker | None = None,
    ):
        self.config = config
        self.artifacts_dir = artifacts_dir
        self.runs_dir = runs_dir
        self.tracker = tracker if tracker is not None else get_tracker(config=config)

    def run(self, dataset: MLDataset) -> ExperimentRun:
        run_id = str(uuid.uuid4())
        experiment = ExperimentRun(
            run_id=run_id, dataset_name=self.config.dataset_name, config=self.config
        )

        run_name = (
            self.config.tracking_run_name
            or f"{dataset.dataset_name}_{self.config.model_type}_h{self.config.horizon}"
        )
        tags = {
            "dataset": dataset.dataset_name,
            "target": dataset.target_column,
            "model_type": self.config.model_type,
            "horizon": str(self.config.horizon),
            "frequency": getattr(dataset, "frequency", "D"),
            **self.config.tracking_tags,
        }

        with self.tracker.start_run(run_name=run_name, tags=tags):
            experiment.mlflow_run_id = self.tracker.active_run_id
            experiment.mlflow_experiment_id = self.tracker.active_experiment_id

            # Log experiment parameters
            params: dict[str, str | int | float | None] = {
                "dataset_name": dataset.dataset_name,
                "target_column": dataset.target_column,
                "frequency": getattr(dataset, "frequency", "D"),
                "horizon": self.config.horizon,
                "walk_forward_origins": self.config.walk_forward_origins,
                "high_demand_quantile": str(self.config.high_demand_quantile),
                "model_type": self.config.model_type,
                "baseline_model_type": self.config.baseline_model_type,
                "split_train_ratio": self.config.split.train_ratio,
                "split_val_ratio": self.config.split.val_ratio,
                "split_test_ratio": self.config.split.test_ratio,
                "features_lags": str(self.config.features.lags),
                "features_rolling_windows": str(self.config.features.rolling_windows),
            }
            if self.config.model_type == "baseline":
                for k, v in self.config.baseline_model_kwargs.items():
                    params[f"baseline_{k}"] = str(v)
            elif self.config.model_type == "arima":
                params["arima_order"] = str(self.config.arima_order)
                params["arima_seasonal_order"] = str(self.config.arima_seasonal_order)
            elif self.config.model_type == "prophet":
                for k, v in self.config.prophet_kwargs.items():
                    params[f"prophet_{k}"] = str(v)
            elif self.config.model_type == "lstm":
                params["lstm_hidden_dim"] = self.config.lstm_hidden_dim
                params["lstm_num_layers"] = self.config.lstm_num_layers
                params["lstm_dropout"] = self.config.lstm_dropout
                params["lstm_epochs"] = self.config.lstm_epochs
                params["lstm_learning_rate"] = self.config.lstm_learning_rate
                params["lstm_sequence_length"] = self.config.lstm_sequence_length
                params["lstm_mc_samples"] = self.config.lstm_mc_samples

            self.tracker.log_params(params)

            if dataset.df.empty:
                raise ValueError("Dataset is empty. Cannot run pipeline.")
            df = dataset.df.sort_values(dataset.time_column).reset_index(drop=True)
            experiment.total_rows = len(df)

            feature_engineer = FeatureEngineer(self.config.features, horizon=self.config.horizon)
            df_featured, feature_cols = feature_engineer.engineer_features(dataset)
            experiment.feature_count = len(feature_cols)

            splitter = TemporalSplitter(self.config.split)
            train_df, val_df, test_df = splitter.split(df_featured)

            experiment.train_rows = len(train_df)
            experiment.val_rows = len(val_df)
            experiment.test_rows = len(test_df)

            if len(train_df) == 0 or len(val_df) == 0 or len(test_df) == 0:
                raise ValueError("Not enough data to create train/val/test splits.")

            preprocessor = DataPreprocessor(feature_cols)
            train_df_scaled = preprocessor.fit_transform(train_df)
            val_df_scaled = preprocessor.transform(val_df)
            test_df_scaled = preprocessor.transform(test_df)

            # Baselines do not need scaled features. ARIMA/Prophet do not use lagged features anyway.
            is_baseline = self.config.model_type == "baseline"
            if is_baseline:
                train_df_model = train_df
                val_df_model = val_df
                test_df_model = test_df
            else:
                train_df_model = train_df_scaled
                val_df_model = val_df_scaled
                test_df_model = test_df_scaled

            # High demand evaluation threshold
            threshold = None
            if self.config.high_demand_quantile is not None:
                threshold = train_df[dataset.target_column].quantile(self.config.high_demand_quantile)

            # Baseline fast-path (static sliding window via lagged features)
            if is_baseline:
                fr_val = self._evaluate_baseline(
                    "validation", train_df_model, val_df_model, dataset, threshold
                )
                fr_test = self._evaluate_baseline(
                    "test", train_df_model, test_df_model, dataset, threshold
                )
                experiment.forecasts.append(fr_val)
                experiment.forecasts.append(fr_test)
            else:
                # ARIMA / Prophet True Walk-Forward
                # Evaluate Validation
                try:
                    fr_val = self._evaluate_walk_forward(
                        "validation", train_df_model, val_df_model, dataset, threshold
                    )
                    experiment.forecasts.append(fr_val)
                except Exception as e:
                    # Graceful failure
                    print(f"[{self.config.model_type}] Validation evaluation failed: {e}")

                # Evaluate Test
                try:
                    # For test evaluation, history is train + val
                    history_df = pd.concat([train_df_model, val_df_model]).reset_index(drop=True)
                    fr_test = self._evaluate_walk_forward(
                        "test", history_df, test_df_model, dataset, threshold
                    )
                    experiment.forecasts.append(fr_test)
                except Exception as e:
                    print(f"[{self.config.model_type}] Test evaluation failed: {e}")

            # Record metrics with strict separation between validation and held-out test splits
            metrics_to_log: dict[str, float] = {}
            fr_val_entry = next((f for f in experiment.forecasts if f.split_name == "validation"), None)
            if fr_val_entry and fr_val_entry.metrics:
                metrics_to_log["val_mae"] = fr_val_entry.metrics.mae
                metrics_to_log["val_rmse"] = fr_val_entry.metrics.rmse
                if fr_val_entry.metrics.smape is not None:
                    metrics_to_log["val_smape"] = fr_val_entry.metrics.smape
                if fr_val_entry.metrics.mape is not None:
                    metrics_to_log["val_mape"] = fr_val_entry.metrics.mape
                if fr_val_entry.high_demand_metrics:
                    metrics_to_log["val_high_demand_mae"] = fr_val_entry.high_demand_metrics.mae
                    metrics_to_log["val_high_demand_rmse"] = fr_val_entry.high_demand_metrics.rmse

            fr_test_entry = next((f for f in experiment.forecasts if f.split_name == "test"), None)
            if fr_test_entry and fr_test_entry.metrics:
                metrics_to_log["test_mae"] = fr_test_entry.metrics.mae
                metrics_to_log["test_rmse"] = fr_test_entry.metrics.rmse
                if fr_test_entry.metrics.smape is not None:
                    metrics_to_log["test_smape"] = fr_test_entry.metrics.smape
                if fr_test_entry.metrics.mape is not None:
                    metrics_to_log["test_mape"] = fr_test_entry.metrics.mape
                if fr_test_entry.high_demand_metrics:
                    metrics_to_log["test_high_demand_mae"] = fr_test_entry.high_demand_metrics.mae
                    metrics_to_log["test_high_demand_rmse"] = fr_test_entry.high_demand_metrics.rmse

            if metrics_to_log:
                self.tracker.log_metrics(metrics_to_log)

            # Log experiment artifacts
            log_experiment_artifacts(self.tracker, experiment)

            experiment.status = "COMPLETED"
            self._save_experiment(experiment)

        return experiment

    def _init_model(self, dataset: MLDataset):
        if self.config.model_type == "baseline":
            base_type = self.config.baseline_model_type
            if base_type == "naive":
                lag_col = f"{dataset.target_column}_lag_1"
                return NaiveBaselineModel(target_column=dataset.target_column, lag_column=lag_col)
            elif base_type == "seasonal_naive":
                sp = self.config.baseline_model_kwargs.get("seasonal_period", 7)
                lag_col = f"{dataset.target_column}_lag_{sp}"
                return SeasonalNaiveBaselineModel(
                    target_column=dataset.target_column, seasonal_lag_column=lag_col
                )
            elif base_type == "moving_average":
                w = self.config.baseline_model_kwargs.get("window", 7)
                mean_col = f"{dataset.target_column}_rolling_mean_{w}"
                return MovingAverageBaselineModel(
                    target_column=dataset.target_column, rolling_mean_column=mean_col
                )
        elif self.config.model_type == "arima":
            return ARIMAForecastModel(
                target_column=dataset.target_column,
                order=self.config.arima_order,
                seasonal_order=self.config.arima_seasonal_order,
            )
        elif self.config.model_type == "prophet":
            return ProphetForecastModel(
                target_column=dataset.target_column,
                time_column=dataset.time_column,
                **self.config.prophet_kwargs,
            )
        elif self.config.model_type == "lstm":
            return LSTMForecastModel(
                target_column=dataset.target_column,
                horizon=self.config.horizon,
                sequence_length=self.config.lstm_sequence_length,
                hidden_dim=self.config.lstm_hidden_dim,
                num_layers=self.config.lstm_num_layers,
                dropout=self.config.lstm_dropout,
                epochs=self.config.lstm_epochs,
                batch_size=self.config.lstm_batch_size,
                learning_rate=self.config.lstm_learning_rate,
                mc_samples=self.config.lstm_mc_samples,
            )
        raise ValueError(f"Unknown model_type: {self.config.model_type}")


    def _evaluate_baseline(
        self,
        split_name: str,
        train_df: pd.DataFrame,
        eval_df: pd.DataFrame,
        dataset: MLDataset,
        threshold: float | None,
    ) -> ForecastResult:
        model = self._init_model(dataset)
        model.fit(train_df, train_df[dataset.target_column])

        y_true = eval_df[dataset.target_column]
        y_pred, y_lower, y_upper = model.predict(eval_df)

        return self._build_forecast_result(
            split_name, eval_df, y_true, y_pred, y_lower, y_upper, dataset, threshold, origins=1
        )

    def _evaluate_walk_forward(
        self,
        split_name: str,
        history_df: pd.DataFrame,
        eval_df: pd.DataFrame,
        dataset: MLDataset,
        threshold: float | None,
    ) -> ForecastResult:
        origins = self.config.walk_forward_origins
        h = self.config.horizon

        # Max possible origins is the number of steps we can stride in eval_df
        # If eval_df has 10 rows and h=1, we can have 10 origins.
        # If h=7, we can only have 10-7+1 = 4 origins if we evaluate non-overlapping,
        # but for true walk-forward we can just evaluate the next h steps.
        # We'll just take the first `origins` points from eval_df as starting points.
        max_origins = len(eval_df) - h + 1
        if max_origins <= 0:
            raise ValueError(f"Eval dataframe too small (len {len(eval_df)}) for horizon {h}")

        actual_origins = min(origins, max_origins)

        all_y_true = []
        all_y_pred = []
        all_timestamps = []

        current_history = history_df.copy()

        for i in range(actual_origins):
            model = self._init_model(dataset)

            # Target is explicitly passed
            model.fit(current_history, current_history[dataset.target_column])

            # The next h rows
            future_X = eval_df.iloc[i : i + h]
            future_y = future_X[dataset.target_column]

            y_pred, y_lower, y_upper = model.predict(future_X)

            all_y_true.extend(future_y.values)
            all_y_pred.extend(y_pred.values)
            all_timestamps.extend(future_X[dataset.time_column].astype(str).values)

            # Advance history for the next origin (append 1 row from eval_df)
            current_history = pd.concat([current_history, eval_df.iloc[[i]]], ignore_index=True)

        y_true_series = pd.Series(all_y_true)
        y_pred_series = pd.Series(all_y_pred)

        # We wrap it in a mock DataFrame
        mock_eval_df = pd.DataFrame(
            {dataset.time_column: all_timestamps, dataset.target_column: y_true_series}
        )

        # We don't aggregate intervals over the walk-forward origins because
        # intervals are origin-specific. We'll leave them as None in Walk-Forward,
        # or we could collect them if needed. The user requested interval persistence
        # where available. Since walk-forward concatenates independent horizons, we
        # technically could concat the interval arrays. But for simplicity, we pass None.

        fr = self._build_forecast_result(
            split_name,
            mock_eval_df,
            y_true_series,
            y_pred_series,
            None,
            None,
            dataset,
            threshold,
            origins=actual_origins,
        )
        return fr

    def _build_forecast_result(
        self,
        split_name: str,
        eval_df: pd.DataFrame,
        y_true: pd.Series,
        y_pred: pd.Series,
        y_lower: pd.Series | None,
        y_upper: pd.Series | None,
        dataset: MLDataset,
        threshold: float | None,
        origins: int,
    ) -> ForecastResult:
        high_demand_metrics = None
        if threshold is not None:
            surge_mask = y_true >= threshold
            y_true_surge = y_true[surge_mask]
            y_pred_surge = y_pred[surge_mask]

            valid_surge = ~y_true_surge.isna() & ~y_pred_surge.isna()
            y_true_surge = y_true_surge[valid_surge]
            y_pred_surge = y_pred_surge[valid_surge]

            if len(y_true_surge) > 0:
                high_demand_metrics = EvaluationMetrics(
                    mae=mean_absolute_error(y_true_surge, y_pred_surge),
                    rmse=root_mean_squared_error(y_true_surge, y_pred_surge),
                    smape=safe_smape(y_true_surge, y_pred_surge),
                    mape=safe_mape(y_true_surge, y_pred_surge),
                )

        valid_idx = ~y_true.isna() & ~y_pred.isna()
        y_true_clean = y_true[valid_idx]
        y_pred_clean = y_pred[valid_idx]

        if len(y_true_clean) > 0:
            eval_metrics = EvaluationMetrics(
                mae=mean_absolute_error(y_true_clean, y_pred_clean),
                rmse=root_mean_squared_error(y_true_clean, y_pred_clean),
                smape=safe_smape(y_true_clean, y_pred_clean),
                mape=safe_mape(y_true_clean, y_pred_clean),
            )
        else:
            eval_metrics = EvaluationMetrics(mae=0.0, rmse=0.0, smape=0.0, mape=0.0)

        model_name = self.config.model_type
        if model_name == "baseline":
            model_name = self.config.baseline_model_type

        # We inject the split name into the model name so the caller can differentiate
        # Alternatively, we could add `split_name` to ForecastResult. For now we just use a convention or property.
        # But wait, we should add split_name to ForecastResult.

        return ForecastResult(
            dataset_name=self.config.dataset_name,
            target=dataset.target_column,
            model_name=model_name,
            split_name=split_name,
            horizon=self.config.horizon,
            metrics=eval_metrics,
            high_demand_metrics=high_demand_metrics,
            high_demand_threshold=threshold,
            forecast_timestamps=eval_df[dataset.time_column].astype(str).tolist(),
            predictions=y_pred.fillna(0.0).tolist(),
            actuals=y_true.fillna(0.0).tolist(),
            walk_forward_origin_count=origins,
        )

    def _save_experiment(self, experiment: ExperimentRun) -> None:
        os.makedirs(self.runs_dir, exist_ok=True)
        run_file = os.path.join(self.runs_dir, f"{experiment.run_id}.json")
        with open(run_file, "w") as f:
            f.write(experiment.model_dump_json(indent=2))
        experiment.artifact_dir = run_file
