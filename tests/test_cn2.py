"""
Tests for the CN2 Rule Induction Algorithm.

This module tests the CN2Classifier implementation including:
- Basic fitting and prediction
- Rule learning with different parameters
- Handling of categorical and numeric features
- Edge cases and error handling
"""

import pytest
import pandas as pd
import numpy as np
from collections import Counter

from sqlshell.utils.profile_cn2 import (
    CN2Classifier,
    Condition,
    Rule,
    fit_cn2,
)


# ==============================================================================
# Fixtures
# ==============================================================================

@pytest.fixture
def simple_classification_df():
    """Create a simple dataset for binary classification."""
    np.random.seed(42)
    n = 100
    
    # Clear separation between classes
    data = {
        'feature1': np.concatenate([
            np.random.uniform(0, 5, n // 2),
            np.random.uniform(5, 10, n // 2)
        ]),
        'feature2': np.concatenate([
            np.random.uniform(0, 3, n // 2),
            np.random.uniform(3, 6, n // 2)
        ]),
        'target': ['class_A'] * (n // 2) + ['class_B'] * (n // 2)
    }
    return pd.DataFrame(data)


@pytest.fixture
def multiclass_df():
    """Create a dataset for multiclass classification."""
    np.random.seed(42)
    n = 150
    
    data = {
        'sepal_length': np.concatenate([
            np.random.normal(5.0, 0.3, 50),
            np.random.normal(6.0, 0.4, 50),
            np.random.normal(6.5, 0.4, 50)
        ]),
        'petal_length': np.concatenate([
            np.random.normal(1.4, 0.2, 50),
            np.random.normal(4.2, 0.4, 50),
            np.random.normal(5.5, 0.5, 50)
        ]),
        'species': ['setosa'] * 50 + ['versicolor'] * 50 + ['virginica'] * 50
    }
    return pd.DataFrame(data)


@pytest.fixture
def categorical_df():
    """Create a dataset with categorical features."""
    np.random.seed(42)
    n = 100
    
    colors = np.random.choice(['red', 'green', 'blue'], n)
    sizes = np.random.choice(['small', 'medium', 'large'], n)
    
    # Target based on categorical values
    target = []
    for i in range(n):
        if colors[i] == 'red':
            target.append('A')
        elif sizes[i] == 'large':
            target.append('B')
        else:
            target.append('A')
    
    data = {
        'color': colors,
        'size': sizes,
        'target': target
    }
    return pd.DataFrame(data)


@pytest.fixture
def mixed_df():
    """Create a dataset with mixed feature types."""
    np.random.seed(42)
    n = 100
    
    data = {
        'numeric_feat': np.random.uniform(0, 10, n),
        'categorical_feat': np.random.choice(['cat1', 'cat2', 'cat3'], n),
        'binary_feat': np.random.choice([0, 1], n),
        'target': np.random.choice(['yes', 'no'], n)
    }
    return pd.DataFrame(data)


@pytest.fixture
def cn2_classifier():
    """Create a default CN2Classifier instance."""
    return CN2Classifier(
        beam_width=5,
        min_covered_examples=5,
        quality_measure='likelihood_ratio'
    )


# ==============================================================================
# Test Condition Class
# ==============================================================================

class TestCondition:
    """Tests for the Condition data class."""
    
    def test_categorical_condition_str(self):
        """Test string representation of categorical condition."""
        cond = Condition(feature='color', operator='==', value='red', is_numeric=False)
        assert str(cond) == "color == 'red'"
    
    def test_numeric_condition_str(self):
        """Test string representation of numeric condition."""
        cond = Condition(feature='age', operator='<=', value=25.5, is_numeric=True)
        assert 'age <=' in str(cond)
        assert '25.5' in str(cond)
    
    def test_condition_equality(self):
        """Test condition equality comparison."""
        cond1 = Condition('x', '==', 'a')
        cond2 = Condition('x', '==', 'a')
        cond3 = Condition('x', '==', 'b')
        
        assert cond1 == cond2
        assert cond1 != cond3
    
    def test_condition_hash(self):
        """Test condition hashing for use in sets."""
        cond1 = Condition('x', '==', 'a')
        cond2 = Condition('x', '==', 'a')
        
        # Same conditions should have same hash
        assert hash(cond1) == hash(cond2)
        
        # Should be usable in sets
        cond_set = {cond1, cond2}
        assert len(cond_set) == 1
    
    def test_condition_evaluate_categorical(self):
        """Test evaluating categorical condition on data."""
        cond = Condition('color', '==', 'red')
        
        row1 = pd.Series({'color': 'red', 'size': 10})
        row2 = pd.Series({'color': 'blue', 'size': 10})
        
        assert cond.evaluate(row1) == True
        assert cond.evaluate(row2) == False
    
    def test_condition_evaluate_numeric_le(self):
        """Test evaluating numeric <= condition."""
        cond = Condition('age', '<=', 30, is_numeric=True)
        
        row1 = pd.Series({'age': 25})
        row2 = pd.Series({'age': 35})
        row3 = pd.Series({'age': 30})
        
        assert cond.evaluate(row1) == True
        assert cond.evaluate(row2) == False
        assert cond.evaluate(row3) == True
    
    def test_condition_evaluate_numeric_gt(self):
        """Test evaluating numeric > condition."""
        cond = Condition('age', '>', 30, is_numeric=True)
        
        row1 = pd.Series({'age': 25})
        row2 = pd.Series({'age': 35})
        
        assert cond.evaluate(row1) == False
        assert cond.evaluate(row2) == True
    
    def test_condition_evaluate_nan(self):
        """Test that NaN values return False."""
        cond = Condition('value', '==', 10)
        row = pd.Series({'value': np.nan})
        
        assert cond.evaluate(row) == False


# ==============================================================================
# Test Rule Class
# ==============================================================================

class TestRule:
    """Tests for the Rule data class."""
    
    def test_empty_rule_str(self):
        """Test string representation of empty rule."""
        rule = Rule(predicted_class='A')
        assert 'True' in str(rule)
        assert 'class = A' in str(rule)
    
    def test_rule_with_conditions_str(self):
        """Test string representation of rule with conditions."""
        rule = Rule(
            conditions=[
                Condition('x', '==', 'a'),
                Condition('y', '<=', 5, is_numeric=True)
            ],
            predicted_class='B',
            coverage=50,
            accuracy=0.8
        )
        rule_str = str(rule)
        
        assert "x == 'a'" in rule_str
        assert 'y <=' in rule_str
        assert 'class = B' in rule_str
        assert '80' in rule_str  # Accept 80% or 80.00%
    
    def test_rule_covers_empty_conditions(self):
        """Test that empty rule covers all rows."""
        rule = Rule()
        row = pd.Series({'a': 1, 'b': 2})
        
        assert rule.covers(row) == True
    
    def test_rule_covers_matching(self):
        """Test rule coverage for matching row."""
        rule = Rule(
            conditions=[
                Condition('color', '==', 'red'),
                Condition('size', '>', 5, is_numeric=True)
            ]
        )
        
        row_match = pd.Series({'color': 'red', 'size': 10})
        row_no_match = pd.Series({'color': 'blue', 'size': 10})
        
        assert rule.covers(row_match) == True
        assert rule.covers(row_no_match) == False
    
    def test_rule_covers_mask(self):
        """Test rule coverage mask for DataFrame."""
        rule = Rule(
            conditions=[Condition('x', '>', 5, is_numeric=True)]
        )
        
        X = pd.DataFrame({'x': [1, 5, 10, 15]})
        mask = rule.covers_mask(X)
        
        expected = np.array([False, False, True, True])
        np.testing.assert_array_equal(mask, expected)
    
    def test_rule_to_dict(self):
        """Test rule conversion to dictionary."""
        rule = Rule(
            conditions=[Condition('x', '==', 'a')],
            predicted_class='Y',
            coverage=100,
            accuracy=0.9,
            class_distribution={'Y': 90, 'N': 10}
        )
        
        d = rule.to_dict()
        
        assert d['predicted_class'] == 'Y'
        assert d['coverage'] == 100
        assert d['accuracy'] == 0.9
        assert len(d['conditions']) == 1


# ==============================================================================
# Test CN2Classifier Initialization
# ==============================================================================

class TestCN2ClassifierInit:
    """Tests for CN2Classifier initialization."""
    
    def test_default_parameters(self):
        """Test default parameter values."""
        clf = CN2Classifier()
        
        assert clf.max_rules == 10  # Changed default for performance
        assert clf.beam_width == 3  # Changed default for performance
        assert clf.min_covered_examples == 5
        assert clf.max_rule_length == 3  # Changed default for performance
        assert clf.quality_measure == 'likelihood_ratio'
        assert clf.laplace_smoothing == True
    
    def test_custom_parameters(self):
        """Test custom parameter initialization."""
        clf = CN2Classifier(
            max_rules=10,
            beam_width=10,
            min_covered_examples=3,
            max_rule_length=5,
            quality_measure='entropy',
            discretization_bins=10
        )
        
        assert clf.max_rules == 10
        assert clf.beam_width == 10
        assert clf.min_covered_examples == 3
        assert clf.max_rule_length == 5
        assert clf.quality_measure == 'entropy'
        assert clf.discretization_bins == 10
    
    def test_invalid_quality_measure(self):
        """Test that invalid quality measure raises error."""
        with pytest.raises(ValueError, match="quality_measure"):
            CN2Classifier(quality_measure='invalid')


# ==============================================================================
# Test CN2Classifier Fitting
# ==============================================================================

class TestCN2ClassifierFit:
    """Tests for CN2Classifier fitting."""
    
    def test_fit_simple_data(self, cn2_classifier, simple_classification_df):
        """Test fitting on simple binary classification data."""
        X = simple_classification_df.drop(columns=['target'])
        y = simple_classification_df['target'].values
        
        clf = cn2_classifier.fit(X, y)
        
        assert clf._is_fitted == True
        assert len(clf.rules_) > 0
        assert len(clf.classes_) == 2
        assert clf.default_class_ is not None
    
    def test_fit_multiclass(self, cn2_classifier, multiclass_df):
        """Test fitting on multiclass data."""
        X = multiclass_df.drop(columns=['species'])
        y = multiclass_df['species'].values
        
        clf = cn2_classifier.fit(X, y)
        
        assert clf._is_fitted == True
        assert len(clf.classes_) == 3
        assert 'setosa' in clf.classes_
        assert 'versicolor' in clf.classes_
        assert 'virginica' in clf.classes_
    
    def test_fit_categorical_features(self, cn2_classifier, categorical_df):
        """Test fitting on categorical features."""
        X = categorical_df.drop(columns=['target'])
        y = categorical_df['target'].values
        
        clf = cn2_classifier.fit(X, y)
        
        assert clf._is_fitted == True
        assert len(clf.rules_) > 0
        
        # Check that categorical conditions are learned
        all_conditions = []
        for rule in clf.rules_:
            all_conditions.extend(rule.conditions)
        
        # Should have some categorical conditions
        cat_conditions = [c for c in all_conditions if c.operator == '==']
        assert len(cat_conditions) > 0
    
    def test_fit_returns_self(self, cn2_classifier, simple_classification_df):
        """Test that fit returns self for chaining."""
        X = simple_classification_df.drop(columns=['target'])
        y = simple_classification_df['target'].values
        
        result = cn2_classifier.fit(X, y)
        
        assert result is cn2_classifier
    
    def test_fit_numpy_array(self, cn2_classifier):
        """Test fitting with numpy arrays."""
        np.random.seed(42)
        X = np.random.rand(100, 3)
        y = np.random.choice(['A', 'B'], 100)
        
        clf = cn2_classifier.fit(X, y)
        
        assert clf._is_fitted == True
        assert clf.n_features_ == 3
    
    def test_fit_empty_raises_error(self, cn2_classifier):
        """Test that fitting on empty data raises error."""
        X = pd.DataFrame(columns=['a', 'b'])
        y = np.array([])
        
        with pytest.raises(ValueError, match="empty"):
            cn2_classifier.fit(X, y)
    
    def test_fit_mismatched_lengths_raises_error(self, cn2_classifier):
        """Test that mismatched X and y lengths raises error."""
        X = pd.DataFrame({'a': [1, 2, 3]})
        y = np.array(['A', 'B'])
        
        with pytest.raises(ValueError, match="same length"):
            cn2_classifier.fit(X, y)


# ==============================================================================
# Test CN2Classifier Prediction
# ==============================================================================

class TestCN2ClassifierPredict:
    """Tests for CN2Classifier prediction."""
    
    def test_predict_basic(self, cn2_classifier, simple_classification_df):
        """Test basic prediction."""
        X = simple_classification_df.drop(columns=['target'])
        y = simple_classification_df['target'].values
        
        clf = cn2_classifier.fit(X, y)
        predictions = clf.predict(X)
        
        assert len(predictions) == len(y)
        assert set(predictions).issubset(set(y))
    
    def test_predict_not_fitted_raises_error(self, cn2_classifier):
        """Test that predicting without fitting raises error."""
        X = pd.DataFrame({'a': [1, 2, 3]})
        
        with pytest.raises(RuntimeError, match="not fitted"):
            cn2_classifier.predict(X)
    
    def test_predict_proba_shape(self, cn2_classifier, simple_classification_df):
        """Test predict_proba output shape."""
        X = simple_classification_df.drop(columns=['target'])
        y = simple_classification_df['target'].values
        
        clf = cn2_classifier.fit(X, y)
        proba = clf.predict_proba(X)
        
        assert proba.shape == (len(X), len(clf.classes_))
    
    def test_predict_proba_sums_to_one(self, cn2_classifier, simple_classification_df):
        """Test that predicted probabilities sum to 1."""
        X = simple_classification_df.drop(columns=['target'])
        y = simple_classification_df['target'].values
        
        clf = cn2_classifier.fit(X, y)
        proba = clf.predict_proba(X)
        
        row_sums = proba.sum(axis=1)
        np.testing.assert_array_almost_equal(row_sums, np.ones(len(X)))
    
    def test_predict_proba_valid_range(self, cn2_classifier, simple_classification_df):
        """Test that probabilities are in [0, 1]."""
        X = simple_classification_df.drop(columns=['target'])
        y = simple_classification_df['target'].values
        
        clf = cn2_classifier.fit(X, y)
        proba = clf.predict_proba(X)
        
        assert np.all(proba >= 0)
        assert np.all(proba <= 1)


# ==============================================================================
# Test CN2Classifier Scoring
# ==============================================================================

class TestCN2ClassifierScore:
    """Tests for CN2Classifier scoring."""
    
    def test_score_basic(self, cn2_classifier, simple_classification_df):
        """Test basic accuracy scoring."""
        X = simple_classification_df.drop(columns=['target'])
        y = simple_classification_df['target'].values
        
        clf = cn2_classifier.fit(X, y)
        score = clf.score(X, y)
        
        assert 0 <= score <= 1
    
    def test_score_perfect_separation(self):
        """Test score on perfectly separable data."""
        # Create perfectly separable data
        X = pd.DataFrame({
            'feature': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        })
        y = np.array(['A', 'A', 'A', 'A', 'A', 'B', 'B', 'B', 'B', 'B'])
        
        clf = CN2Classifier(min_covered_examples=2)
        clf.fit(X, y)
        score = clf.score(X, y)
        
        # Should achieve high accuracy on separable data
        assert score >= 0.8


# ==============================================================================
# Test CN2Classifier Rules
# ==============================================================================

class TestCN2ClassifierRules:
    """Tests for rule retrieval methods."""
    
    def test_get_rules(self, cn2_classifier, simple_classification_df):
        """Test get_rules method."""
        X = simple_classification_df.drop(columns=['target'])
        y = simple_classification_df['target'].values
        
        clf = cn2_classifier.fit(X, y)
        rules = clf.get_rules()
        
        assert isinstance(rules, list)
        assert all(isinstance(r, Rule) for r in rules)
    
    def test_get_rules_not_fitted(self, cn2_classifier):
        """Test get_rules raises error when not fitted."""
        with pytest.raises(RuntimeError, match="not fitted"):
            cn2_classifier.get_rules()
    
    def test_get_rules_as_df(self, cn2_classifier, simple_classification_df):
        """Test get_rules_as_df method."""
        X = simple_classification_df.drop(columns=['target'])
        y = simple_classification_df['target'].values
        
        clf = cn2_classifier.fit(X, y)
        rules_df = clf.get_rules_as_df()
        
        assert isinstance(rules_df, pd.DataFrame)
        assert 'rule_id' in rules_df.columns
        assert 'conditions' in rules_df.columns
        assert 'predicted_class' in rules_df.columns
        assert 'coverage' in rules_df.columns
        assert 'accuracy' in rules_df.columns
    
    def test_rules_have_valid_metrics(self, cn2_classifier, simple_classification_df):
        """Test that rules have valid metric values."""
        X = simple_classification_df.drop(columns=['target'])
        y = simple_classification_df['target'].values
        
        clf = cn2_classifier.fit(X, y)
        
        for rule in clf.get_rules():
            assert rule.coverage >= clf.min_covered_examples
            assert 0 <= rule.accuracy <= 1
            assert rule.predicted_class in clf.classes_


# ==============================================================================
# Test CN2Classifier Parameters
# ==============================================================================

class TestCN2ClassifierParameters:
    """Tests for different parameter configurations."""
    
    def test_max_rules_limit(self, simple_classification_df):
        """Test max_rules parameter limits number of rules."""
        X = simple_classification_df.drop(columns=['target'])
        y = simple_classification_df['target'].values
        
        clf = CN2Classifier(max_rules=2, min_covered_examples=5)
        clf.fit(X, y)
        
        assert len(clf.rules_) <= 2
    
    def test_max_rule_length(self, mixed_df):
        """Test max_rule_length parameter."""
        X = mixed_df.drop(columns=['target'])
        y = mixed_df['target'].values
        
        clf = CN2Classifier(max_rule_length=2, min_covered_examples=5)
        clf.fit(X, y)
        
        for rule in clf.rules_:
            assert len(rule.conditions) <= 2
    
    def test_beam_width_affects_search(self, multiclass_df):
        """Test that different beam widths can produce different results."""
        X = multiclass_df.drop(columns=['species'])
        y = multiclass_df['species'].values
        
        clf_narrow = CN2Classifier(beam_width=1, random_state=42)
        clf_wide = CN2Classifier(beam_width=10, random_state=42)
        
        clf_narrow.fit(X, y)
        clf_wide.fit(X, y)
        
        # Both should produce valid rules
        assert len(clf_narrow.rules_) > 0
        assert len(clf_wide.rules_) > 0
    
    def test_entropy_quality_measure(self, simple_classification_df):
        """Test entropy quality measure works."""
        X = simple_classification_df.drop(columns=['target'])
        y = simple_classification_df['target'].values
        
        clf = CN2Classifier(quality_measure='entropy', min_covered_examples=5)
        clf.fit(X, y)
        
        assert clf._is_fitted
        assert len(clf.rules_) > 0
    
    def test_random_state_reproducibility(self, simple_classification_df):
        """Test random_state produces reproducible results."""
        X = simple_classification_df.drop(columns=['target'])
        y = simple_classification_df['target'].values
        
        clf1 = CN2Classifier(random_state=42)
        clf2 = CN2Classifier(random_state=42)
        
        clf1.fit(X, y)
        clf2.fit(X, y)
        
        # Same random state should produce same rules
        assert len(clf1.rules_) == len(clf2.rules_)


# ==============================================================================
# Test fit_cn2 Convenience Function
# ==============================================================================

class TestFitCN2Function:
    """Tests for the fit_cn2 convenience function."""
    
    def test_fit_cn2_basic(self, simple_classification_df):
        """Test basic usage of fit_cn2."""
        clf = fit_cn2(simple_classification_df, 'target')
        
        assert isinstance(clf, CN2Classifier)
        assert clf._is_fitted
    
    def test_fit_cn2_with_kwargs(self, simple_classification_df):
        """Test fit_cn2 with additional parameters."""
        clf = fit_cn2(
            simple_classification_df, 
            'target',
            beam_width=10,
            min_covered_examples=3
        )
        
        assert clf.beam_width == 10
        assert clf.min_covered_examples == 3
    
    def test_fit_cn2_invalid_target(self, simple_classification_df):
        """Test fit_cn2 with invalid target column."""
        with pytest.raises(ValueError, match="not found"):
            fit_cn2(simple_classification_df, 'nonexistent')


# ==============================================================================
# Test Edge Cases
# ==============================================================================

class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""
    
    def test_single_feature(self):
        """Test with single feature."""
        X = pd.DataFrame({'x': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]})
        y = np.array(['A', 'A', 'A', 'A', 'A', 'B', 'B', 'B', 'B', 'B'])
        
        clf = CN2Classifier(min_covered_examples=2)
        clf.fit(X, y)
        
        assert clf._is_fitted
    
    def test_single_class(self):
        """Test with single class (all same label)."""
        X = pd.DataFrame({'x': [1, 2, 3, 4, 5]})
        y = np.array(['A', 'A', 'A', 'A', 'A'])
        
        clf = CN2Classifier(min_covered_examples=2)
        clf.fit(X, y)
        
        # Should work but may not learn useful rules
        assert clf._is_fitted
        assert clf.default_class_ == 'A'
    
    def test_with_nan_values(self):
        """Test handling of NaN values in features."""
        X = pd.DataFrame({
            'x': [1, 2, np.nan, 4, 5, 6, 7, np.nan, 9, 10],
            'y': [1, np.nan, 3, 4, 5, 6, 7, 8, 9, 10]
        })
        y = np.array(['A', 'A', 'A', 'A', 'A', 'B', 'B', 'B', 'B', 'B'])
        
        clf = CN2Classifier(min_covered_examples=2)
        clf.fit(X, y)
        
        # Should still work
        assert clf._is_fitted
        predictions = clf.predict(X)
        assert len(predictions) == len(y)
    
    def test_all_nan_column(self):
        """Test dataset with a column that is entirely NaN."""
        X = pd.DataFrame({
            'good': [1, 2, 3, 4, 5],
            'all_nan': [np.nan, np.nan, np.nan, np.nan, np.nan]
        })
        y = np.array(['A', 'B', 'A', 'B', 'A'])
        
        clf = CN2Classifier(min_covered_examples=1)
        clf.fit(X, y)
        
        assert clf._is_fitted
        # Should not raise any errors
        predictions = clf.predict(X)
        assert len(predictions) == len(y)
    
    def test_only_nan_features(self):
        """Test dataset where all features are NaN."""
        X = pd.DataFrame({
            'nan1': [np.nan] * 10,
            'nan2': [np.nan] * 10
        })
        y = np.array(['A'] * 5 + ['B'] * 5)
        
        clf = CN2Classifier(min_covered_examples=2)
        clf.fit(X, y)
        
        # Should fit without errors, but no rules learned
        assert clf._is_fitted
        assert len(clf.rules_) == 0
        assert clf.default_class_ == 'A'  # Majority class
        
        # Predictions should fall back to default class
        predictions = clf.predict(X)
        assert all(p == clf.default_class_ for p in predictions)
    
    def test_many_features(self):
        """Test with many features."""
        np.random.seed(42)
        n_features = 20
        X = pd.DataFrame(
            np.random.rand(100, n_features),
            columns=[f'feat_{i}' for i in range(n_features)]
        )
        y = np.random.choice(['A', 'B'], 100)
        
        clf = CN2Classifier(min_covered_examples=5, max_rule_length=3)
        clf.fit(X, y)
        
        assert clf._is_fitted
        assert clf.n_features_ == n_features
    
    def test_special_characters_in_values(self):
        """Test with special characters in categorical values."""
        X = pd.DataFrame({
            'category': ["value-1", "value_2", "value.3", "value 4", "value-1"]
        })
        y = np.array(['A', 'B', 'A', 'B', 'A'])
        
        clf = CN2Classifier(min_covered_examples=1)
        clf.fit(X, y)
        
        assert clf._is_fitted
    
    def test_mixed_nan_values(self):
        """Test with NaN values scattered throughout the data."""
        X = pd.DataFrame({
            'x': [1, np.nan, 3, np.nan, 5, 6, np.nan, 8, 9, 10],
            'y': ['a', 'b', np.nan, 'a', 'b', 'a', 'b', np.nan, 'a', 'b']
        })
        y = np.array(['Y', 'Y', 'Y', 'Y', 'Y', 'N', 'N', 'N', 'N', 'N'])
        
        clf = CN2Classifier(min_covered_examples=2)
        clf.fit(X, y)
        
        assert clf._is_fitted
        predictions = clf.predict(X)
        assert len(predictions) == len(y)
    
    def test_very_small_dataset(self):
        """Test with minimal dataset (2 samples)."""
        X = pd.DataFrame({'x': [1, 2]})
        y = np.array(['A', 'B'])
        
        clf = CN2Classifier(min_covered_examples=1)
        clf.fit(X, y)
        
        assert clf._is_fitted
    
    def test_high_nan_ratio(self):
        """Test with high ratio of NaN values."""
        np.random.seed(42)
        X = pd.DataFrame({
            'x': [np.nan if i % 3 == 0 else i for i in range(20)],
            'y': [np.nan if i % 4 == 0 else i * 2 for i in range(20)]
        })
        y = np.array(['A'] * 10 + ['B'] * 10)
        
        clf = CN2Classifier(min_covered_examples=2)
        clf.fit(X, y)
        
        assert clf._is_fitted
        predictions = clf.predict(X)
        assert len(predictions) == len(y)
    
    def test_nan_in_target(self):
        """Test with NaN values in target column (critical edge case)."""
        X = pd.DataFrame({
            'x': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
        })
        y = np.array(['A', 'B', np.nan, 'A', 'B', 'A', np.nan, 'B', 'A', 'B'])
        
        clf = CN2Classifier(min_covered_examples=2)
        clf.fit(X, y)
        
        assert clf._is_fitted
        # Should have filtered out NaN rows
        assert 'nan' not in [str(c).lower() for c in clf.classes_]
    
    def test_numeric_target_with_nan(self):
        """Test with numeric target that has NaN values."""
        X = pd.DataFrame({
            'x': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
        })
        y = np.array([1, 2, np.nan, 1, 2, 1, np.nan, 2, 1, 2])
        
        clf = CN2Classifier(min_covered_examples=2)
        clf.fit(X, y)
        
        assert clf._is_fitted
        # Classes should be converted to strings
        assert all(isinstance(c, (str, np.str_)) for c in clf.classes_)


# ==============================================================================
# Integration Tests
# ==============================================================================

class TestIntegration:
    """Integration tests for full workflow."""
    
    def test_full_workflow(self, multiclass_df):
        """Test complete fit-predict-evaluate workflow."""
        # Split data
        train_idx = np.random.choice(len(multiclass_df), 100, replace=False)
        test_idx = np.array([i for i in range(len(multiclass_df)) if i not in train_idx])
        
        train_df = multiclass_df.iloc[train_idx]
        test_df = multiclass_df.iloc[test_idx]
        
        X_train = train_df.drop(columns=['species'])
        y_train = train_df['species'].values
        X_test = test_df.drop(columns=['species'])
        y_test = test_df['species'].values
        
        # Fit
        clf = CN2Classifier(beam_width=5, min_covered_examples=5)
        clf.fit(X_train, y_train)
        
        # Predict
        predictions = clf.predict(X_test)
        proba = clf.predict_proba(X_test)
        
        # Evaluate
        train_score = clf.score(X_train, y_train)
        test_score = clf.score(X_test, y_test)
        
        # Get rules
        rules = clf.get_rules()
        rules_df = clf.get_rules_as_df()
        
        # Assertions
        assert len(predictions) == len(y_test)
        assert proba.shape[1] == len(clf.classes_)
        assert 0 <= train_score <= 1
        assert 0 <= test_score <= 1
        assert len(rules) > 0
        assert len(rules_df) == len(rules)
    
    def test_consistent_predictions(self, simple_classification_df):
        """Test that predictions are consistent across multiple calls."""
        X = simple_classification_df.drop(columns=['target'])
        y = simple_classification_df['target'].values
        
        clf = CN2Classifier(random_state=42)
        clf.fit(X, y)
        
        pred1 = clf.predict(X)
        pred2 = clf.predict(X)
        
        np.testing.assert_array_equal(pred1, pred2)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

