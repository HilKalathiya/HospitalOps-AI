import logging

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from sklearn.preprocessing import StandardScaler
from torch.utils.data import DataLoader, TensorDataset

from app.ml.contracts.model import ForecastModel

logger = logging.getLogger(__name__)


class HospitalLSTMNet(nn.Module):
    """
    Multi-layer LSTM Neural Network with Dropout and Dense Projection Head
    for Multi-Horizon Hospital Capacity & Admission Demand Forecasting.
    """

    def __init__(
        self,
        input_dim: int,
        hidden_dim: int = 64,
        num_layers: int = 2,
        dropout: float = 0.2,
        horizon: int = 1,
    ):
        super().__init__()
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers
        self.horizon = horizon

        self.lstm = nn.LSTM(
            input_size=input_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0.0,
        )
        self.dropout = nn.Dropout(p=dropout)
        self.fc = nn.Linear(hidden_dim, horizon)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        x shape: (batch_size, sequence_length, input_dim)
        output shape: (batch_size, horizon)
        """
        out, (hn, cn) = self.lstm(x)
        # Use last sequence step hidden state
        last_hidden = out[:, -1, :]
        dropped = self.dropout(last_hidden)
        preds = self.fc(dropped)
        return preds


class LSTMForecastModel(ForecastModel):
    """
    Deep Learning LSTM Forecasting Model conforming to the HospitalOps AI ForecastModel contract.
    Supports multi-feature sequence windowing, multi-horizon prediction, and Monte Carlo
    Dropout uncertainty bounds (95% CI).
    """

    def __init__(
        self,
        target_column: str,
        horizon: int = 1,
        sequence_length: int = 14,
        hidden_dim: int = 64,
        num_layers: int = 2,
        dropout: float = 0.2,
        epochs: int = 25,
        batch_size: int = 32,
        learning_rate: float = 0.005,
        mc_samples: int = 20,
        seed: int = 42,
    ):
        self.target_column = target_column
        self.horizon = max(1, horizon)
        self.sequence_length = sequence_length
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers
        self.dropout = dropout
        self.epochs = epochs
        self.batch_size = batch_size
        self.learning_rate = learning_rate
        self.mc_samples = mc_samples
        self.seed = seed

        self.device = torch.device("cpu")
        self.model: HospitalLSTMNet | None = None
        self.target_scaler = StandardScaler()
        self.feature_cols: list[str] = []
        self._last_train_features: np.ndarray | None = None

    def _prepare_feature_matrix(self, X: pd.DataFrame) -> np.ndarray:
        """Extracts and aligns strictly numeric feature columns."""
        if not self.feature_cols:
            # First time in fit: select all numeric columns
            numeric_cols = [
                col
                for col in X.columns
                if pd.api.types.is_numeric_dtype(X[col]) and col != self.target_column
            ]
            self.feature_cols = numeric_cols

        # Fill NaNs with 0.0 for stability
        df_feat = X[self.feature_cols].copy().fillna(0.0)
        return df_feat.values.astype(np.float32)

    def _create_sliding_windows(
        self, features: np.ndarray, targets: np.ndarray, seq_len: int, horizon: int
    ) -> tuple[np.ndarray, np.ndarray]:
        """
        Creates strictly backward-looking sliding sequence windows:
        Input window: features[i : i + seq_len]
        Target window: targets[i + seq_len : i + seq_len + horizon]
        Guarantees zero future lookahead.
        """
        n_samples = len(features)
        X_seq, y_seq = [], []

        for i in range(n_samples - seq_len - horizon + 1):
            x_window = features[i : i + seq_len]
            y_window = targets[i + seq_len : i + seq_len + horizon]
            X_seq.append(x_window)
            y_seq.append(y_window)

        return np.array(X_seq, dtype=np.float32), np.array(y_seq, dtype=np.float32)

    def fit(self, X_train: pd.DataFrame, y_train: pd.Series) -> None:
        """
        Trains the LSTM model with standard AdamW optimization and gradient clipping.
        """
        # Set seeds for reproducibility
        torch.manual_seed(self.seed)
        np.random.seed(self.seed)

        features = self._prepare_feature_matrix(X_train)
        input_dim = features.shape[1]
        if input_dim == 0:
            raise ValueError("No numeric features found to train LSTM model.")

        y_raw = y_train.ffill().fillna(0.0).values.reshape(-1, 1)
        y_scaled = self.target_scaler.fit_transform(y_raw).flatten()

        # Adjust sequence_length downward if dataset is small
        min_required = self.horizon + 4
        actual_seq_len = self.sequence_length
        if len(features) < actual_seq_len + self.horizon:
            actual_seq_len = max(2, len(features) - self.horizon - 1)
            self.sequence_length = actual_seq_len

        if len(features) < min_required:
            raise ValueError(
                f"Training set size ({len(features)}) is too small for horizon ({self.horizon})."
            )

        X_seq, y_seq = self._create_sliding_windows(
            features, y_scaled, self.sequence_length, self.horizon
        )

        if len(X_seq) == 0:
            raise ValueError("Could not construct sequence windows from training data.")

        # Cache last sequence window for future single-step or horizon prediction
        self._last_train_features = features[-self.sequence_length :]

        dataset = TensorDataset(torch.from_numpy(X_seq), torch.from_numpy(y_seq))
        loader = DataLoader(
            dataset, batch_size=min(self.batch_size, len(dataset)), shuffle=True
        )

        self.model = HospitalLSTMNet(
            input_dim=input_dim,
            hidden_dim=self.hidden_dim,
            num_layers=self.num_layers,
            dropout=self.dropout,
            horizon=self.horizon,
        ).to(self.device)

        criterion = nn.SmoothL1Loss()
        optimizer = torch.optim.AdamW(
            self.model.parameters(), lr=self.learning_rate, weight_decay=1e-4
        )

        self.model.train()
        for _epoch in range(self.epochs):
            for batch_x, batch_y in loader:

                batch_x = batch_x.to(self.device)
                batch_y = batch_y.to(self.device)

                optimizer.zero_grad()
                preds = self.model(batch_x)
                loss = criterion(preds, batch_y)
                loss.backward()
                nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)
                optimizer.step()

    def predict(
        self, X: pd.DataFrame
    ) -> tuple[pd.Series, pd.Series | None, pd.Series | None]:
        """
        Predicts future values with Monte Carlo Dropout uncertainty bounds.
        Returns: (y_pred, y_lower, y_upper)
        """
        if self.model is None or self._last_train_features is None:
            raise ValueError("LSTM model is not fitted.")

        steps = len(X)
        if steps == 0:
            return pd.Series([], index=X.index), None, None

        features = self._prepare_feature_matrix(X)

        # Form the input sequence:
        # If X contains features of length >= sequence_length, use trailing slice
        if len(features) >= self.sequence_length:
            input_seq = features[-self.sequence_length :]
        else:
            # Combine trailing training features with X features
            combined = np.vstack([self._last_train_features, features])
            input_seq = combined[-self.sequence_length :]

        x_tensor = torch.from_numpy(input_seq).unsqueeze(0).to(self.device)

        # Monte Carlo Dropout for Uncertainty Estimation
        # Enable dropout during evaluation passes
        self.model.train()
        mc_predictions = []

        with torch.no_grad():
            for _ in range(max(1, self.mc_samples)):
                out = self.model(x_tensor)  # (1, horizon)
                pred_scaled = out.cpu().numpy().flatten()
                # Inverse transform to original target units
                pred_orig = self.target_scaler.inverse_transform(
                    pred_scaled.reshape(-1, 1)
                ).flatten()
                mc_predictions.append(pred_orig)

        mc_array = np.array(mc_predictions)  # (mc_samples, horizon)
        mean_preds = np.mean(mc_array, axis=0)
        std_preds = np.std(mc_array, axis=0)

        # Slice to requested steps
        if steps <= self.horizon:
            y_pred_vals = mean_preds[:steps]
            std_vals = std_preds[:steps]
        else:
            # If steps exceeds model horizon, tile the predictions
            repeats = int(np.ceil(steps / self.horizon))
            y_pred_vals = np.tile(mean_preds, repeats)[:steps]
            std_vals = np.tile(std_preds, repeats)[:steps]

        # Calculate 95% confidence intervals (mean +/- 1.96 * std)
        # Ensure non-negative bounds for hospital capacity
        lower_vals = np.clip(y_pred_vals - 1.96 * std_vals, a_min=0.0, a_max=None)
        upper_vals = np.clip(y_pred_vals + 1.96 * std_vals, a_min=0.0, a_max=None)
        y_pred_vals = np.clip(y_pred_vals, a_min=0.0, a_max=None)

        y_pred = pd.Series(y_pred_vals, index=X.index)
        y_lower = pd.Series(lower_vals, index=X.index)
        y_upper = pd.Series(upper_vals, index=X.index)

        return y_pred, y_lower, y_upper
