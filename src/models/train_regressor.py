import pandas as pd
import numpy as np
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
import xgboost as xgb
from sklearn.model_selection import LeaveOneOut
from sklearn.metrics import mean_absolute_error, r2_score

FEATURE_COLS = ["eps_estimate", "reported_eps", "surprise_pct"]
TARGET_COL = "price_reaction_pct"

if __name__ == "__main__":
    df = pd.read_csv("data/processed/regression_target_v2.csv")
    X = df[FEATURE_COLS]
    y = df[TARGET_COL]

    loo = LeaveOneOut()

    for model_name, model_fn in [
        ("XGBoost", lambda: xgb.XGBRegressor(n_estimators=50, max_depth=3, random_state=42)),
        ("Ridge (linear)", lambda: make_pipeline(StandardScaler(), Ridge(alpha=1.0))),
    ]:
        predictions, actuals = [], []
        for train_idx, test_idx in loo.split(X):
            model = model_fn()
            model.fit(X.iloc[train_idx], y.iloc[train_idx])
            predictions.append(model.predict(X.iloc[test_idx])[0])
            actuals.append(y.iloc[test_idx].values[0])

        mae = mean_absolute_error(actuals, predictions)
        r2 = r2_score(actuals, predictions)
        print(f"{model_name}: LOOCV MAE = {mae:.3f}, R² = {r2:.3f}")

    baseline_mae = mean_absolute_error(y, [np.mean(y)] * len(y))
    print(f"Baseline (always predict mean): MAE = {baseline_mae:.3f}")