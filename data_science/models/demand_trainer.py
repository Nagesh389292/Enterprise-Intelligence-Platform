"""
data_science/models/demand_trainer.py
------------------------------------
Production-grade time-series machine learning model training, evaluation,
expanding-window cross-validation, and SHAP explainability pipeline for SKU Demand Forecasting.
"""

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from sklearn.model_selection import TimeSeriesSplit
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import RobustScaler, OneHotEncoder
from sklearn.pipeline import Pipeline
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from xgboost import XGBRegressor
from lightgbm import LGBMRegressor
import shap

from data_science.db import load_demand_features
from data_science.config import FIGURE_DPI


class DemandMLPipeline:
    def __init__(self, random_state: int = 42):
        self.random_state = random_state
        self.num_cols = [
            'units_sold_lag1', 'units_sold_lag7', 'units_sold_lag14', 'units_sold_lag28',
            'rolling_avg_7d', 'rolling_avg_30d', 'rolling_7_std',
            'day_of_week_num', 'month', 'day_of_month'
        ]
        self.cat_cols = ['category_name', 'is_weekend']
        self.target_col = 'units_sold_target'
        self.feature_names = []

    def load_data(self) -> pd.DataFrame:
        """
        Load demand data and construct lag + rolling features per product.
        """
        df = load_demand_features()
        df = df.sort_values(by=['product_id', 'sale_date']).reset_index(drop=True)

        # Construct time-series features
        df['units_sold_lag1'] = df.groupby('product_id')['units_sold_target'].shift(1)
        df['units_sold_lag28'] = df.groupby('product_id')['units_sold_target'].shift(28)
        df['rolling_7_std'] = df.groupby('product_id')['units_sold_target'].transform(
            lambda x: x.shift(1).rolling(7).std()
        )
        df['day_of_month'] = df['sale_date'].dt.day
        df['day_of_week_num'] = df['sale_date'].dt.dayofweek

        # Drop rows with NaN from initial lag shifts (first 28 days)
        df_clean = df.dropna(subset=self.num_cols + [self.target_col]).reset_index(drop=True)
        df_clean = df_clean.sort_values(by='sale_date').reset_index(drop=True)

        return df_clean

    def get_preprocessor(self) -> ColumnTransformer:
        return ColumnTransformer(
            transformers=[
                ('num', RobustScaler(), self.num_cols),
                ('cat', OneHotEncoder(handle_unknown='ignore', sparse_output=False), self.cat_cols)
            ]
        )

    def compute_mape(self, y_true: np.ndarray, y_pred: np.ndarray) -> float:
        """
        Compute Mean Absolute Percentage Error (MAPE) avoiding division by zero.
        """
        y_true_safe = np.maximum(np.abs(y_true), 1.0)
        return float(np.mean(np.abs(y_true - y_pred) / y_true_safe) * 100.0)

    def get_candidate_models(self) -> dict:
        return {
            "Ridge_Linear_Regressor": Ridge(alpha=10.0, random_state=self.random_state),
            "XGBoost_Demand_Regressor": XGBRegressor(
                n_estimators=80, max_depth=4, learning_rate=0.05,
                subsample=0.8, colsample_bytree=0.8, n_jobs=-1, random_state=self.random_state
            ),
            "LightGBM_Demand_Regressor": LGBMRegressor(
                n_estimators=80, max_depth=4, learning_rate=0.05,
                subsample=0.8, colsample_bytree=0.8, n_jobs=-1, random_state=self.random_state, verbose=-1
            )
        }

    def evaluate_all_models(self, df: pd.DataFrame, n_splits: int = 5) -> tuple[dict, dict]:
        """
        Run 5-Fold Expanding Window TimeSeriesSplit CV.
        """
        X = df[self.num_cols + self.cat_cols]
        y = df[self.target_col].values

        tscv = TimeSeriesSplit(n_splits=n_splits)
        models = self.get_candidate_models()

        results = {}
        oof_predictions = {}

        # 1. Evaluate Rule-based Baselines
        # Naïve Lag-7 Baseline
        naive_mapes = []
        naive_rmses = []
        naive_oof = np.full(len(y), np.nan)

        for train_idx, val_idx in tscv.split(X):
            y_val = y[val_idx]
            y_pred_naive = df.iloc[val_idx]['units_sold_lag7'].values
            naive_oof[val_idx] = y_pred_naive
            naive_mapes.append(self.compute_mape(y_val, y_pred_naive))
            naive_rmses.append(np.sqrt(mean_squared_error(y_val, y_pred_naive)))

        results["Naive_Lag7_Baseline"] = {
            "mape_mean": float(np.mean(naive_mapes)),
            "mape_std": float(np.std(naive_mapes)),
            "rmse_mean": float(np.mean(naive_rmses)),
            "mae_mean": float(mean_absolute_error(y[~np.isnan(naive_oof)], naive_oof[~np.isnan(naive_oof)])),
            "r2_mean": float(r2_score(y[~np.isnan(naive_oof)], naive_oof[~np.isnan(naive_oof)]))
        }
        oof_predictions["Naive_Lag7_Baseline"] = naive_oof

        # Rolling 7-day Mean Baseline
        roll_mapes = []
        roll_rmses = []
        roll_oof = np.full(len(y), np.nan)

        for train_idx, val_idx in tscv.split(X):
            y_val = y[val_idx]
            y_pred_roll = df.iloc[val_idx]['rolling_avg_7d'].values
            roll_oof[val_idx] = y_pred_roll
            roll_mapes.append(self.compute_mape(y_val, y_pred_roll))
            roll_rmses.append(np.sqrt(mean_squared_error(y_val, y_pred_roll)))

        results["Rolling_7d_Mean_Baseline"] = {
            "mape_mean": float(np.mean(roll_mapes)),
            "mape_std": float(np.std(roll_mapes)),
            "rmse_mean": float(np.mean(roll_rmses)),
            "mae_mean": float(mean_absolute_error(y[~np.isnan(roll_oof)], roll_oof[~np.isnan(roll_oof)])),
            "r2_mean": float(r2_score(y[~np.isnan(roll_oof)], roll_oof[~np.isnan(roll_oof)]))
        }
        oof_predictions["Rolling_7d_Mean_Baseline"] = roll_oof

        # 2. Evaluate ML Regressors
        for mname, model in models.items():
            fold_mapes = []
            fold_rmses = []
            fold_maes = []
            fold_r2s = []
            ml_oof = np.full(len(y), np.nan)

            for train_idx, val_idx in tscv.split(X):
                X_train, X_val = X.iloc[train_idx], X.iloc[val_idx]
                y_train, y_val = y[train_idx], y[val_idx]

                pipeline = Pipeline([
                    ('prep', self.get_preprocessor()),
                    ('model', model)
                ])

                pipeline.fit(X_train, y_train)
                preds = np.maximum(pipeline.predict(X_val), 0.0)  # Non-negative demand constraint
                ml_oof[val_idx] = preds

                fold_mapes.append(self.compute_mape(y_val, preds))
                fold_rmses.append(np.sqrt(mean_squared_error(y_val, preds)))
                fold_maes.append(mean_absolute_error(y_val, preds))
                fold_r2s.append(r2_score(y_val, preds))

            results[mname] = {
                "mape_mean": float(np.mean(fold_mapes)),
                "mape_std": float(np.std(fold_mapes)),
                "rmse_mean": float(np.mean(fold_rmses)),
                "mae_mean": float(np.mean(fold_maes)),
                "r2_mean": float(np.mean(fold_r2s))
            }
            oof_predictions[mname] = ml_oof

        return results, oof_predictions

    def train_champion_model(self, df: pd.DataFrame, model_name: str = "Ridge_Linear_Regressor"):
        """
        Fit final champion pipeline on full dataset and return fitted pipeline + preprocessed X matrix.
        """
        X = df[self.num_cols + self.cat_cols]
        y = df[self.target_col].values

        models = self.get_candidate_models()
        chosen_model = models[model_name]

        pipeline = Pipeline([
            ('prep', self.get_preprocessor()),
            ('model', chosen_model)
        ])

        pipeline.fit(X, y)

        prep = pipeline.named_steps['prep']
        cat_encoder = prep.named_transformers_['cat']
        cat_feature_names = cat_encoder.get_feature_names_out(self.cat_cols).tolist()
        self.feature_names = self.num_cols + cat_feature_names

        X_trans = prep.transform(X)
        X_trans_df = pd.DataFrame(X_trans, columns=self.feature_names)

        return pipeline, X_trans_df

    def compute_shap(self, pipeline: Pipeline, X_trans_df: pd.DataFrame) -> tuple[np.ndarray, shap.Explainer]:
        model = pipeline.named_steps['model']
        if hasattr(model, 'coef_'):
            explainer = shap.LinearExplainer(model, X_trans_df)
            shap_values = explainer.shap_values(X_trans_df)
        else:
            explainer = shap.TreeExplainer(model)
            shap_values = explainer.shap_values(X_trans_df)
        return shap_values, explainer
