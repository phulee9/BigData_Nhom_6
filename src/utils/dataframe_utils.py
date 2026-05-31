import ast

import numpy as np
import pandas as pd


def safe_col(df: pd.DataFrame, col: str, default="") -> pd.Series:
    """
    Safely get a column from DataFrame, return default Series if column doesn't exist.
    
    Args:
        df: Input DataFrame
        col: Column name
        default: Default value if column doesn't exist
        
    Returns:
        pd.Series with column data or default values
    """
    if col in df.columns:
        return df[col]

    return pd.Series([default] * len(df), index=df.index)


def parse_skills(value) -> list[str]:
    """
    Parse skills from various data formats (list, tuple, array, string, etc).
    Handles None, NaN, and different serialization formats.
    
    Args:
        value: Skill data in various formats
        
    Returns:
        List of cleaned skill strings
    """
    if value is None:
        return []

    if isinstance(value, float) and pd.isna(value):
        return []

    if isinstance(value, list):
        return [str(s).strip() for s in value if str(s).strip()]

    if isinstance(value, np.ndarray):
        return [str(s).strip() for s in value.tolist() if str(s).strip()]

    if isinstance(value, (tuple, set)):
        return [str(s).strip() for s in list(value) if str(s).strip()]

    if isinstance(value, str):
        text_value = value.strip()

        if text_value.lower() in ["", "[]", "nan", "none", "null"]:
            return []

        try:
            parsed = ast.literal_eval(text_value)

            if isinstance(parsed, list):
                return [str(s).strip() for s in parsed if str(s).strip()]

            if isinstance(parsed, (tuple, set)):
                return [str(s).strip() for s in list(parsed) if str(s).strip()]

        except Exception:
            pass

        return [s.strip() for s in text_value.split(",") if s.strip()]

    return []
