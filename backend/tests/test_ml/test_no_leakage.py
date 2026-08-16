import pandas as pd

from app.ml.contracts.config import FeatureConfig, SplitConfig
from app.ml.contracts.dataset import MLDataset
from app.ml.features.engineer import FeatureEngineer
from app.ml.splitting.temporal import TemporalSplitter


def test_no_future_leakage():
    """
    Tests that mutating a target at t=N does NOT affect any features generated for t < N.
    """
    # Create simple dataset: 1 to 10
    dates = pd.date_range("2026-01-01", periods=10, freq="D")
    df1 = pd.DataFrame({"date": dates, "y": list(range(1, 11))})
    ds1 = MLDataset(
        dataset_name="test",
        source_collection="test",
        df=df1,
        target_column="y",
        time_column="date",
        frequency="D",
        metadata={},
    )

    # Mutate t=5 (index 5, which is day 6, value 6 -> 999)
    df2 = df1.copy()
    df2.loc[5, "y"] = 999
    ds2 = MLDataset(
        dataset_name="test",
        source_collection="test",
        df=df2,
        target_column="y",
        time_column="date",
        frequency="D",
        metadata={},
    )

    config = FeatureConfig(lags=[1, 2], rolling_windows=[3])
    engineer = FeatureEngineer(config)

    res1, _ = engineer.engineer_features(ds1)
    res2, _ = engineer.engineer_features(ds2)

    # The engineered features for index 0 to 4 MUST be identical between res1 and res2
    # Because target(t=5) should only affect features at t > 5.

    # Compare feature rows where index < 5
    # Note that res1 and res2 might have dropped some initial NaN rows if dropna was applied.
    # We must match by 'date'.

    merged = pd.merge(res1, res2, on="date", suffixes=("_1", "_2"))

    # Dates before the mutation (index 5 is 2026-01-06)
    before_mutation = merged[merged["date"] <= pd.Timestamp("2026-01-06")]

    for feature in ["y_lag_1", "y_lag_2", "y_rolling_mean_3"]:
        col1 = f"{feature}_1"
        col2 = f"{feature}_2"
        # They should be perfectly identical before the mutation
        pd.testing.assert_series_equal(
            before_mutation[col1], before_mutation[col2], check_names=False
        )


def test_no_leakage_between_splits():
    """
    Tests that TemporalSplitter strictly respects chronological boundaries.
    """
    dates = pd.date_range("2026-01-01", periods=100, freq="D")
    df = pd.DataFrame({"date": dates, "y": range(100)})

    config = SplitConfig(train_ratio=0.7, val_ratio=0.15, test_ratio=0.15)
    splitter = TemporalSplitter(config)

    train, val, test = splitter.split(df)

    # Verify no overlap and strict chronological order
    assert train["date"].max() < val["date"].min()
    assert val["date"].max() < test["date"].min()
