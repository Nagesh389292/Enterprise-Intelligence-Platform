"""
data_science/models/churn_trainer.py
------------------------------------
Production-grade machine learning model training, evaluation, threshold tuning,
and SHAP explainability pipeline for Customer Churn prediction.
"""

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

from sklearn.model_selection import StratifiedKFold
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import RobustScaler, OneHotEncoder
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier
from lightgbm import LGBMClassifier

from sklearn.metrics import (
    roc_auc_score,
    precision_recall_curve,
    auc,
    precision_score,
    recall_score,
    f1_score,
    accuracy_score,
    brier_score_loss,
    confusion_matrix,
    roc_curve
)
import shap

from data_science.db import load_churn_features
from data_science.config import PALETTE, FIGURE_DPI


class ChurnMLPipeline:
    def __init__(self, random_state: int = 42):
        self.random_state = random_state
        self.num_cols = [
            'total_orders', 'total_revenue', 'avg_order_value',
            'days_since_last_order', 'avg_csat_score', 'total_support_tickets',
            'days_as_customer', 'order_frequency_30d', 'order_frequency_90d'
        ]
        self.cat_cols = ['customer_segment', 'state']
        self.target_col = 'is_churned_target'
        self.preprocessor = None
        self.feature_names = []

    def load_data(self) -> tuple[pd.DataFrame, pd.Series]:
        df = load_churn_features()
        X = df[self.num_cols + self.cat_cols].copy()
        y = df[self.target_col].copy()
        return X, y

    def get_preprocessor(self) -> ColumnTransformer:
        return ColumnTransformer(
            transformers=[
                ('num', RobustScaler(), self.num_cols),
                ('cat', OneHotEncoder(handle_unknown='ignore', sparse_output=False), self.cat_cols)
            ]
        )

    def get_candidate_models(self) -> dict:
        """
        Returns candidate models including baseline and non-linear boosting models.
        """
        pos_weight = (1000 - 44) / 44.0  # 21.727
        return {
            "Logistic_Regression_Baseline": LogisticRegression(
                penalty='l2', C=1.0, max_iter=1000, random_state=self.random_state
            ),
            "Logistic_Regression_Balanced": LogisticRegression(
                penalty='l2', C=1.0, class_weight='balanced', max_iter=1000, random_state=self.random_state
            ),
            "Random_Forest_Balanced": RandomForestClassifier(
                n_estimators=100, max_depth=6, class_weight='balanced', random_state=self.random_state
            ),
            "XGBoost_ScalePosWeight": XGBClassifier(
                n_estimators=100, max_depth=4, learning_rate=0.05,
                scale_pos_weight=pos_weight, eval_metric='logloss', random_state=self.random_state
            ),
            "LightGBM_Unbalanced": LGBMClassifier(
                n_estimators=100, max_depth=4, learning_rate=0.05,
                is_unbalance=True, random_state=self.random_state, verbose=-1
            )
        }

    def evaluate_all_models(self, X: pd.DataFrame, y: pd.Series, n_splits: int = 5) -> dict:
        """
        Run 5-Fold Stratified CV for all candidate models and collect metrics + OOF predictions.
        """
        models = self.get_candidate_models()
        cv = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=self.random_state)

        results = {}
        oof_predictions = {}

        for model_name, model in models.items():
            fold_metrics = []
            oof_probs = np.zeros(len(y))

            for fold, (train_idx, val_idx) in enumerate(cv.split(X, y)):
                X_train, X_val = X.iloc[train_idx], X.iloc[val_idx]
                y_train, y_val = y.iloc[train_idx], y.iloc[val_idx]

                pipeline = Pipeline([
                    ('prep', self.get_preprocessor()),
                    ('model', model)
                ])

                pipeline.fit(X_train, y_train)

                if hasattr(pipeline, "predict_proba"):
                    probs = pipeline.predict_proba(X_val)[:, 1]
                else:
                    probs = pipeline.decision_function(X_val)

                oof_probs[val_idx] = probs

                # Default 0.50 threshold metrics
                preds_50 = (probs >= 0.50).astype(int)

                p_precision, p_recall, _ = precision_recall_curve(y_val, probs)
                pr_auc_val = auc(p_recall, p_precision)
                roc_auc_val = roc_auc_score(y_val, probs)

                fold_metrics.append({
                    'roc_auc': roc_auc_val,
                    'pr_auc': pr_auc_val,
                    'precision_50': precision_score(y_val, preds_50, zero_division=0),
                    'recall_50': recall_score(y_val, preds_50, zero_division=0),
                    'f1_50': f1_score(y_val, preds_50, zero_division=0),
                    'brier': brier_score_loss(y_val, probs)
                })

            oof_predictions[model_name] = oof_probs

            # Aggregated CV summary
            roc_aucs = [m['roc_auc'] for m in fold_metrics]
            pr_aucs = [m['pr_auc'] for m in fold_metrics]
            f1s = [m['f1_50'] for m in fold_metrics]

            results[model_name] = {
                'roc_auc_mean': float(np.mean(roc_aucs)),
                'roc_auc_std': float(np.std(roc_aucs)),
                'pr_auc_mean': float(np.mean(pr_aucs)),
                'pr_auc_std': float(np.std(pr_aucs)),
                'f1_50_mean': float(np.mean(f1s)),
                'brier_mean': float(np.mean([m['brier'] for m in fold_metrics])),
                'fold_metrics': fold_metrics
            }

        return results, oof_predictions

    def optimize_threshold(self, y_true: np.ndarray, y_probs: np.ndarray) -> dict:
        """
        Grid search threshold T from 0.05 to 0.95 to maximize F1 and F2 scores.
        """
        thresholds = np.linspace(0.05, 0.95, 181)
        records = []

        best_f1 = -1.0
        best_t_f1 = 0.50
        best_f2 = -1.0
        best_t_f2 = 0.50

        for t in thresholds:
            preds = (y_probs >= t).astype(int)
            prec = precision_score(y_true, preds, zero_division=0)
            rec = recall_score(y_true, preds, zero_division=0)
            f1 = f1_score(y_true, preds, zero_division=0)
            
            # F2-score weights recall 2x higher than precision (crucial for churn)
            f2 = (5 * prec * rec / (4 * prec + rec)) if (4 * prec + rec) > 0 else 0.0

            if f1 > best_f1:
                best_f1 = f1
                best_t_f1 = t
            if f2 > best_f2:
                best_f2 = f2
                best_t_f2 = t

            records.append({
                'threshold': float(t),
                'precision': float(prec),
                'recall': float(rec),
                'f1': float(f1),
                'f2': float(f2)
            })

        df_thresh = pd.DataFrame(records)

        return {
            'best_threshold_f1': float(best_t_f1),
            'best_f1': float(best_f1),
            'best_threshold_f2': float(best_t_f2),
            'best_f2': float(best_f2),
            'threshold_curve': df_thresh
        }

    def train_champion_model(self, X: pd.DataFrame, y: pd.Series, model_name: str = "XGBoost_ScalePosWeight"):
        """
        Fit final champion pipeline on full dataset and return fitted pipeline + preprocessed X matrix.
        """
        models = self.get_candidate_models()
        chosen_model = models[model_name]

        pipeline = Pipeline([
            ('prep', self.get_preprocessor()),
            ('model', chosen_model)
        ])

        pipeline.fit(X, y)

        # Extract transformed feature names
        prep = pipeline.named_steps['prep']
        cat_encoder = prep.named_transformers_['cat']
        cat_feature_names = cat_encoder.get_feature_names_out(self.cat_cols).tolist()
        self.feature_names = self.num_cols + cat_feature_names

        X_trans = prep.transform(X)
        X_trans_df = pd.DataFrame(X_trans, columns=self.feature_names)

        return pipeline, X_trans_df

    def compute_shap(self, pipeline: Pipeline, X_trans_df: pd.DataFrame) -> tuple[np.ndarray, shap.Explainer]:
        """
        Compute SHAP values for tree model.
        """
        model = pipeline.named_steps['model']
        explainer = shap.TreeExplainer(model)
        shap_values = explainer.shap_values(X_trans_df)
        return shap_values, explainer
