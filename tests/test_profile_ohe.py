import pandas as pd
import numpy as np

from sqlshell.utils.profile_ohe import find_related_ohe_features, build_drilldown_query


def test_related_ohe_drilldown_alignment_with_missing_target():
    # Include a missing target row to ensure it is dropped and alignment is preserved
    df = pd.DataFrame({
        "stars": [5, 4, 5, 1, np.nan, 2, 3],
        "description": [
            "python great",      # python
            "rust ok",           # rust
            "python rust",       # python + rust
            "unknown",           # neither
            "python only",       # python but target is NaN (should be dropped)
            "rustacean rust",    # rust
            "python python"      # python
        ]
    })

    result = find_related_ohe_features(df, "stars", sample_size=100, max_features=10)
    sample_df = result["sample_df"]
    target_values = result["target_values"]

    # Target values should match the cleaned/sample DataFrame exactly
    assert len(target_values) == len(sample_df)
    pd.testing.assert_series_equal(
        target_values.reset_index(drop=True),
        sample_df["stars"].reset_index(drop=True),
        check_names=False,
    )

    # Locate the python-related feature to verify means line up with manual grouping
    python_res = next(r for r in result["results"] if r["feature"] == "has_python")
    feature_series = python_res["feature_series"]
    assert len(feature_series) == len(sample_df)

    mask = feature_series != 0
    present_mean = target_values[mask].mean()
    absent_mean = target_values[~mask].mean()

    expected_present = sample_df.loc[mask, "stars"].mean()
    expected_absent = sample_df.loc[~mask, "stars"].mean()

    assert present_mean == expected_present
    assert absent_mean == expected_absent


def test_build_drilldown_query_word_and_category():
    query_word = build_drilldown_query("repos", "description", "has_python")
    assert "FROM repos" in query_word
    assert "description" in query_word
    assert "LIKE '%python%'" in query_word

    query_cat = build_drilldown_query("repos", "language", "is_Rust")
    assert "language" in query_cat
    assert "= 'Rust'" in query_cat

    # Handles tables we cannot resolve
    assert build_drilldown_query(None, "col", "has_word") is None
