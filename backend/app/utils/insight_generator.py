"""
Statistical insight generator — runs on a freshly-parsed dataset's DataFrame
to surface outliers, data-quality issues, and skew without any LLM call.
"""

from typing import Any

import numpy as np
import pandas as pd
import structlog

logger = structlog.get_logger(__name__)

# Tuning constants
OUTLIER_Z_THRESHOLD = 3.0
HIGH_NULL_RATIO = 0.20  # >20% missing values on a column
SKEW_THRESHOLD = 2.0  # |skew| above this is "heavily skewed"
MAX_INSIGHTS = 10  # cap per dataset to avoid flooding the UI
MIN_ROWS_FOR_STATS = 5  # too few rows makes z-score/skew meaningless


class InsightGenerator:
    """Generates statistical Insight records from a parsed DataFrame."""

    def generate(self, df: pd.DataFrame) -> list[dict[str, Any]]:
        """
        Returns a list of insight dicts ready to be inserted as Insight rows.
        Each dict has: insight_type, title, description, affected_columns,
        severity, confidence_score, insight_metadata.
        """
        if len(df) < MIN_ROWS_FOR_STATS:
            return []

        insights: list[dict[str, Any]] = []
        insights.extend(self._detect_missing_data(df))
        insights.extend(self._detect_outliers(df))
        insights.extend(self._detect_skew(df))

        return insights[:MAX_INSIGHTS]

    def _detect_missing_data(self, df: pd.DataFrame) -> list[dict[str, Any]]:
        results = []
        for col in df.columns:
            series = df[col]
            null_ratio = series.isna().mean()
            if null_ratio > HIGH_NULL_RATIO:
                pct = round(null_ratio * 100, 1)
                severity = "high" if null_ratio > 0.5 else "medium"
                results.append(
                    {
                        "insight_type": "data_quality",
                        "title": f"High missing data in '{col}'",
                        "description": (
                            f"Column '{col}' has {pct}% missing values "
                            f"({series.isna().sum()} of {len(series)} rows)."
                        ),
                        "affected_columns": [str(col)],
                        "severity": severity,
                        "confidence_score": 1.0,
                        "insight_metadata": {"null_ratio": round(null_ratio, 4)},
                    }
                )
        return results

    def _detect_outliers(self, df: pd.DataFrame) -> list[dict[str, Any]]:
        results = []
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            series = df[col].dropna()
            if len(series) < MIN_ROWS_FOR_STATS or series.std() == 0:
                continue

            z_scores = (series - series.mean()) / series.std()
            outlier_mask = z_scores.abs() > OUTLIER_Z_THRESHOLD
            outlier_count = int(outlier_mask.sum())

            if outlier_count == 0:
                continue

            outlier_ratio = outlier_count / len(series)
            severity = "high" if outlier_ratio > 0.05 else "medium"
            sample_values = series[outlier_mask].head(5).round(2).tolist()

            results.append(
                {
                    "insight_type": "outlier",
                    "title": f"Outliers detected in '{col}'",
                    "description": (
                        f"{outlier_count} value(s) in '{col}' are more than "
                        f"{OUTLIER_Z_THRESHOLD:.0f} standard deviations from the mean "
                        f"(mean={series.mean():.2f}, std={series.std():.2f})."
                    ),
                    "affected_columns": [str(col)],
                    "severity": severity,
                    "confidence_score": 0.85,
                    "insight_metadata": {
                        "outlier_count": outlier_count,
                        "sample_values": sample_values,
                    },
                }
            )
        return results

    def _detect_skew(self, df: pd.DataFrame) -> list[dict[str, Any]]:
        results = []
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            series = df[col].dropna()
            if len(series) < MIN_ROWS_FOR_STATS or series.std() == 0:
                continue

            skewness = series.skew()
            if abs(skewness) < SKEW_THRESHOLD:
                continue

            direction = "right" if skewness > 0 else "left"
            results.append(
                {
                    "insight_type": "trend",
                    "title": f"'{col}' is heavily {direction}-skewed",
                    "description": (
                        f"The distribution of '{col}' is heavily skewed "
                        f"({direction}, skewness={skewness:.2f}), meaning most values "
                        f"cluster {'low' if direction == 'right' else 'high'} with a "
                        f"long tail toward "
                        f"{'high' if direction == 'right' else 'low'} values."
                    ),
                    "affected_columns": [str(col)],
                    "severity": "low",
                    "confidence_score": 0.75,
                    "insight_metadata": {"skewness": round(float(skewness), 3)},
                }
            )
        return results
