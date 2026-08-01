import pandas as pd
import numpy as np
from sklearn.model_selection import LeaveOneOut
from sklearn.metrics import mean_absolute_error, r2_score
import xgboost as xgb

FEATURE_COLS = [
    "Revenues_latest", "Revenues_growth_qoq",
    "NetIncomeLoss_latest", "NetIncomeLoss_growth_qoq",
    "EarningsPerShareBasic_latest", "EarningsPerShareBasic_growth_qoq",
]
TARGET_COL = "price_reaction_pct"

def load_dataset(path="data/processed/regression_dataset.csv"):
    df = pd.read_csv(path)
    return df

if __name__ == "__main__":
    df = load_dataset()
    X = df[FEATURE_COLS]
    y = df[TARGET_COL]

    loo = LeaveOneOut()
    predictions = []
    actuals = []

    for train_idx, test_idx in loo.split(X):
        X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
        y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]

        model = xgb.XGBRegressor(n_estimators=50, max_depth=3, random_state=42)
        model.fit(X_train, y_train)
        pred = model.predict(X_test)[0]

        predictions.append(pred)
        actuals.append(y_test.values[0])

    mae = mean_absolute_error(actuals, predictions)
    r2 = r2_score(actuals, predictions)

    print(f"LOOCV MAE: {mae:.3f} percentage points")
    print(f"LOOCV R²: {r2:.3f}")
    print(f"\nBaseline (always predict mean): MAE = {mean_absolute_error(actuals, [np.mean(y)]*len(actuals)):.3f}")