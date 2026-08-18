"""
Data Quality Validation Gate & Contract Checker.
Enforces non-null, range, and type contracts on incoming raw DataFrame rows.
"""

import pandas as pd
from typing import Tuple, List, Dict

class QualityValidator:
    def validate_entity(self, entity_name: str, df: pd.DataFrame) -> Tuple[pd.DataFrame, List[Dict]]:
        """
        Validates entity rows. 
        Returns (valid_df, invalid_records_list).
        """
        if df.empty:
            return df, []
            
        invalid_list = []
        valid_mask = pd.Series(True, index=df.index)
        
        # Entity-specific Validation Rules
        if entity_name == "orders":
            # Rule 1: Non-null order_number
            null_ord = df["order_number"].isnull()
            if null_ord.any():
                for idx in df[null_ord].index:
                    invalid_list.append({
                        "row_dict": df.loc[idx].to_dict(),
                        "failed_rule": "NON_NULL_ORDER_NUMBER"
                    })
                valid_mask = valid_mask & (~null_ord)
                
            # Rule 2: Positive total_amount
            neg_amt = (df["total_amount"] < 0)
            if neg_amt.any():
                for idx in df[neg_amt].index:
                    invalid_list.append({
                        "row_dict": df.loc[idx].to_dict(),
                        "failed_rule": "POSITIVE_TOTAL_AMOUNT"
                    })
                valid_mask = valid_mask & (~neg_amt)

        elif entity_name == "order_items":
            neg_qty = (df["quantity"] <= 0)
            if neg_qty.any():
                for idx in df[neg_qty].index:
                    invalid_list.append({
                        "row_dict": df.loc[idx].to_dict(),
                        "failed_rule": "POSITIVE_QUANTITY"
                    })
                valid_mask = valid_mask & (~neg_qty)

        elif entity_name == "machine_telemetry":
            extreme_temp = (df["temperature_c"] > 500.0) | (df["temperature_c"] < -50.0)
            if extreme_temp.any():
                for idx in df[extreme_temp].index:
                    invalid_list.append({
                        "row_dict": df.loc[idx].to_dict(),
                        "failed_rule": "VALID_TEMPERATURE_RANGE"
                    })
                valid_mask = valid_mask & (~extreme_temp)

        elif entity_name == "customer_satisfaction":
            bad_score = (df["score"] < 1) | (df["score"] > 5)
            if bad_score.any():
                for idx in df[bad_score].index:
                    invalid_list.append({
                        "row_dict": df.loc[idx].to_dict(),
                        "failed_rule": "VALID_CSAT_SCORE_RANGE"
                    })
                valid_mask = valid_mask & (~bad_score)

        valid_df = df[valid_mask].copy()
        return valid_df, invalid_list
