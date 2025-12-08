"""
CN2 Rule Induction Algorithm for Classification

This module implements the classic CN2 rule-induction algorithm inspired by
Clark & Niblett (1989). It learns interpretable IF-THEN classification rules
using a separate-and-conquer (cover-and-remove) strategy with beam search.

The algorithm supports:
- Mixed categorical and numeric features
- Supervised discretization for numeric features
- Multiple quality measures (likelihood_ratio, entropy)
- Laplace-smoothed probability estimates

Example usage:
    from sqlshell.utils.profile_cn2 import CN2Classifier, visualize_cn2_rules
    
    clf = CN2Classifier(beam_width=5, min_covered_examples=5)
    clf.fit(X, y)
    predictions = clf.predict(X)
    rules = clf.get_rules()
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional, Any, Union
from collections import Counter
import warnings


# =============================================================================
# Data Structures
# =============================================================================

@dataclass
class Condition:
    """
    A single condition in a rule.
    
    Attributes:
        feature: Name of the feature being tested
        operator: Comparison operator ('==', '<=', '>')
        value: Value to compare against
        is_numeric: Whether this is a numeric condition
    """
    feature: str
    operator: str  # '==' for categorical, '<=' or '>' for numeric
    value: Any
    is_numeric: bool = False
    
    def __str__(self) -> str:
        if self.is_numeric:
            return f"{self.feature} {self.operator} {self.value:.4g}"
        return f"{self.feature} == '{self.value}'"
    
    def __hash__(self) -> int:
        return hash((self.feature, self.operator, str(self.value)))
    
    def __eq__(self, other) -> bool:
        if not isinstance(other, Condition):
            return False
        return (self.feature == other.feature and 
                self.operator == other.operator and 
                str(self.value) == str(other.value))
    
    def evaluate(self, row: pd.Series) -> bool:
        """Evaluate this condition on a single data row."""
        val = row[self.feature]
        if pd.isna(val):
            return False
        if self.operator == '==':
            return val == self.value
        elif self.operator == '<=':
            return val <= self.value
        elif self.operator == '>':
            return val > self.value
        return False


@dataclass
class Rule:
    """
    A classification rule consisting of conditions and a predicted class.
    
    Attributes:
        conditions: List of conditions forming the rule antecedent
        predicted_class: The class label predicted by this rule
        coverage: Number of training examples covered by this rule
        accuracy: Accuracy of this rule on covered examples
        class_distribution: Distribution of classes among covered examples
        quality_score: Quality score used during rule learning
    """
    conditions: List[Condition] = field(default_factory=list)
    predicted_class: Any = None
    coverage: int = 0
    accuracy: float = 0.0
    class_distribution: Dict[Any, int] = field(default_factory=dict)
    quality_score: float = 0.0
    
    def __str__(self) -> str:
        if not self.conditions:
            return f"IF True THEN class = {self.predicted_class}"
        cond_str = " AND ".join(str(c) for c in self.conditions)
        return (f"IF {cond_str} THEN class = {self.predicted_class} "
                f"[cov={self.coverage}, acc={self.accuracy:.2%}]")
    
    def __repr__(self) -> str:
        return self.__str__()
    
    def covers(self, row: pd.Series) -> bool:
        """Check if this rule covers (applies to) a data row."""
        if not self.conditions:
            return True
        return all(cond.evaluate(row) for cond in self.conditions)
    
    def covers_mask(self, X: pd.DataFrame) -> np.ndarray:
        """Return a boolean mask of rows covered by this rule."""
        if not self.conditions:
            return np.ones(len(X), dtype=bool)
        mask = np.ones(len(X), dtype=bool)
        for cond in self.conditions:
            col_vals = X[cond.feature]
            if cond.operator == '==':
                mask &= (col_vals == cond.value).values
            elif cond.operator == '<=':
                mask &= (col_vals <= cond.value).values
            elif cond.operator == '>':
                mask &= (col_vals > cond.value).values
            # Handle NaN values
            mask &= ~col_vals.isna().values
        return mask
    
    def to_dict(self) -> Dict:
        """Convert rule to a dictionary representation."""
        return {
            'conditions': [str(c) for c in self.conditions],
            'conditions_detailed': [
                {'feature': c.feature, 'operator': c.operator, 
                 'value': c.value, 'is_numeric': c.is_numeric}
                for c in self.conditions
            ],
            'predicted_class': self.predicted_class,
            'coverage': self.coverage,
            'accuracy': self.accuracy,
            'class_distribution': dict(self.class_distribution),
            'quality_score': self.quality_score
        }


# =============================================================================
# CN2 Classifier (Optimized)
# =============================================================================

class CN2Classifier:
    """
    CN2 Rule Induction Classifier (Optimized Implementation).
    
    Implements the classic CN2 algorithm for learning classification rules
    using a separate-and-conquer strategy with beam search.
    
    Parameters:
        max_rules: Maximum number of rules to learn (default: 10)
        beam_width: Width of the beam in beam search (default: 3)
        min_covered_examples: Minimum examples a rule must cover (default: 5)
        max_rule_length: Maximum number of conditions per rule (default: 3)
        quality_measure: Quality heuristic - 'likelihood_ratio' or 'entropy'
        random_state: Random seed for reproducibility
        discretization_bins: Number of bins for numeric feature discretization (default: 4)
        laplace_smoothing: Whether to use Laplace smoothing for probabilities
    
    Attributes:
        rules_: List of learned Rule objects (after fitting)
        default_class_: Default class for examples not covered by any rule
        classes_: Unique class labels
        feature_names_: Names of input features
        n_features_: Number of input features
    """
    
    def __init__(
        self,
        max_rules: Optional[int] = 10,
        beam_width: int = 3,
        min_covered_examples: int = 5,
        max_rule_length: Optional[int] = 3,
        quality_measure: str = "likelihood_ratio",
        random_state: Optional[int] = None,
        discretization_bins: int = 4,
        laplace_smoothing: bool = True
    ):
        self.max_rules = max_rules
        self.beam_width = beam_width
        self.min_covered_examples = min_covered_examples
        self.max_rule_length = max_rule_length if max_rule_length else 3
        self.quality_measure = quality_measure
        self.random_state = random_state
        self.discretization_bins = discretization_bins
        self.laplace_smoothing = laplace_smoothing
        
        # Validate quality measure
        if quality_measure not in ('likelihood_ratio', 'entropy'):
            raise ValueError(
                f"quality_measure must be 'likelihood_ratio' or 'entropy', "
                f"got '{quality_measure}'"
            )
        
        # Will be set during fit
        self.rules_: List[Rule] = []
        self.default_class_: Any = None
        self.classes_: np.ndarray = None
        self.feature_names_: List[str] = []
        self.n_features_: int = 0
        self._is_fitted: bool = False
        
        # Cached data for fast computation
        self._X_array: np.ndarray = None
        self._y_array: np.ndarray = None
        self._condition_masks: Dict = {}  # Pre-computed masks for all conditions
        self._feature_conditions: List = []  # List of (feature_idx, operator, value, is_numeric)
    
    def fit(self, X, y) -> "CN2Classifier":
        """
        Learn a rule list from training data.
        
        Parameters:
            X: Feature matrix (pandas DataFrame or 2D numpy array)
            y: Target labels (1D array-like)
        
        Returns:
            self: The fitted classifier
        """
        # Convert inputs to proper format
        X_df, y = self._validate_input(X, y)
        
        # Store class information
        self.classes_ = np.unique(y)
        self.feature_names_ = list(X_df.columns)
        self.n_features_ = len(self.feature_names_)
        
        # Store default class (majority class in training data)
        class_counts = Counter(y)
        self.default_class_ = class_counts.most_common(1)[0][0]
        
        # Convert class labels to integers for faster processing
        self._class_to_idx = {c: i for i, c in enumerate(self.classes_)}
        self._y_encoded = np.array([self._class_to_idx[c] for c in y])
        n_classes = len(self.classes_)
        
        # Pre-compute all condition masks (this is the key optimization)
        self._precompute_condition_masks(X_df)
        
        # Check if we have any valid conditions
        if len(self._feature_conditions) == 0:
            # No valid conditions - can't learn rules, just use default class
            self._is_fitted = True
            return self
        
        # Main CN2 loop: separate-and-conquer
        self.rules_ = []
        remaining_mask = np.ones(len(X_df), dtype=bool)
        n_samples = len(X_df)
        
        while remaining_mask.sum() >= self.min_covered_examples:
            # Check max rules limit
            if self.max_rules is not None and len(self.rules_) >= self.max_rules:
                break
            
            # Find the best rule for remaining examples
            best_rule = self._find_best_rule_fast(remaining_mask)
            
            if best_rule is None:
                break
            
            # Add rule to rule list
            self.rules_.append(best_rule)
            
            # Remove covered examples
            rule_mask = self._compute_rule_mask(best_rule._condition_indices)
            remaining_mask &= ~rule_mask
        
        # Store dataframe for prediction
        self._X_df = X_df
        self._is_fitted = True
        return self
    
    def _precompute_condition_masks(self, X: pd.DataFrame):
        """Pre-compute boolean masks for all possible conditions."""
        self._condition_masks = {}
        self._feature_conditions = []
        n_samples = len(X)
        
        for feat_idx, col in enumerate(X.columns):
            col_data = X[col].values
            dtype = X[col].dtype
            is_numeric = np.issubdtype(dtype, np.number)
            
            # Handle NaN mask
            nan_mask = pd.isna(col_data)
            
            if is_numeric:
                # Get quantile thresholds (fewer bins = faster)
                valid_data = col_data[~nan_mask]
                if len(valid_data) == 0:
                    continue
                    
                n_unique = len(np.unique(valid_data))
                if n_unique <= self.discretization_bins:
                    # Treat as categorical
                    for val in np.unique(valid_data):
                        cond_idx = len(self._feature_conditions)
                        mask = (col_data == val) & ~nan_mask
                        self._condition_masks[cond_idx] = mask
                        self._feature_conditions.append((feat_idx, '==', val, False))
                else:
                    # Use quantile thresholds
                    quantiles = np.linspace(0, 1, self.discretization_bins + 1)[1:-1]
                    thresholds = np.unique(np.quantile(valid_data, quantiles))
                    
                    for thresh in thresholds:
                        # <= condition
                        cond_idx = len(self._feature_conditions)
                        mask = (col_data <= thresh) & ~nan_mask
                        self._condition_masks[cond_idx] = mask
                        self._feature_conditions.append((feat_idx, '<=', thresh, True))
                        
                        # > condition
                        cond_idx = len(self._feature_conditions)
                        mask = (col_data > thresh) & ~nan_mask
                        self._condition_masks[cond_idx] = mask
                        self._feature_conditions.append((feat_idx, '>', thresh, True))
            else:
                # Categorical feature - limit number of values
                unique_vals = pd.Series(col_data).dropna().unique()
                # Limit to top N most frequent values for performance
                if len(unique_vals) > 10:
                    value_counts = pd.Series(col_data).value_counts()
                    unique_vals = value_counts.head(10).index.tolist()
                
                for val in unique_vals:
                    cond_idx = len(self._feature_conditions)
                    mask = (col_data == val) & ~nan_mask
                    self._condition_masks[cond_idx] = mask
                    self._feature_conditions.append((feat_idx, '==', val, False))
    
    def _compute_rule_mask(self, condition_indices: List[int]) -> np.ndarray:
        """Compute mask for a rule given its condition indices."""
        if not condition_indices:
            return np.ones(len(self._y_encoded), dtype=bool)
        
        mask = self._condition_masks[condition_indices[0]].copy()
        for idx in condition_indices[1:]:
            mask &= self._condition_masks[idx]
        return mask
    
    def _find_best_rule_fast(self, remaining_mask: np.ndarray) -> Optional[Rule]:
        """
        Find the best rule using optimized beam search.
        """
        n_samples = remaining_mask.sum()
        if n_samples == 0:
            return None
        
        n_classes = len(self.classes_)
        if n_classes == 0:
            return None
        
        # Check if there are any valid conditions to try
        if len(self._feature_conditions) == 0:
            return None
        
        y_remaining = self._y_encoded[remaining_mask]
        
        # Track best rule found
        best_rule_info = None
        best_quality = float('-inf')
        
        # Beam: list of (condition_indices, quality)
        beam = [([], 0.0)]
        
        for depth in range(self.max_rule_length):
            new_beam = []
            seen_masks = set()  # Avoid duplicate rules
            
            for cond_indices, _ in beam:
                # Get current mask
                if cond_indices:
                    current_mask = self._compute_rule_mask(cond_indices) & remaining_mask
                else:
                    current_mask = remaining_mask.copy()
                
                current_coverage = current_mask.sum()
                if current_coverage < self.min_covered_examples:
                    continue
                
                # Get features already used
                used_features = {self._feature_conditions[i][0] for i in cond_indices}
                
                # Try adding each condition
                for cond_idx, (feat_idx, op, val, is_num) in enumerate(self._feature_conditions):
                    # Skip if feature already used
                    if feat_idx in used_features:
                        continue
                    
                    # Compute combined mask
                    new_mask = current_mask & self._condition_masks[cond_idx]
                    coverage = new_mask.sum()
                    
                    # Skip if insufficient coverage
                    if coverage < self.min_covered_examples:
                        continue
                    
                    # Create hashable key to avoid duplicates
                    mask_key = tuple(sorted(cond_indices + [cond_idx]))
                    if mask_key in seen_masks:
                        continue
                    seen_masks.add(mask_key)
                    
                    # Compute class distribution efficiently
                    y_covered = self._y_encoded[new_mask]
                    class_counts = np.bincount(y_covered, minlength=n_classes)
                    
                    # Compute quality
                    quality = self._compute_quality_fast(class_counts, coverage, n_samples)
                    
                    # Compute accuracy
                    majority_class_count = class_counts.max()
                    accuracy = majority_class_count / coverage
                    
                    # Track best overall
                    if quality > best_quality and accuracy >= 0.5:
                        best_quality = quality
                        best_rule_info = (cond_indices + [cond_idx], class_counts, coverage, accuracy, quality)
                    
                    new_beam.append((cond_indices + [cond_idx], quality))
            
            if not new_beam:
                break
            
            # Keep top beam_width candidates (filter out NaN/inf quality scores)
            new_beam = [(c, q) for c, q in new_beam if not (np.isnan(q) or np.isinf(q) and q < 0)]
            if not new_beam:
                break
            new_beam.sort(key=lambda x: x[1], reverse=True)
            beam = new_beam[:self.beam_width]
        
        # Convert best rule info to Rule object
        if best_rule_info is None:
            return None
        
        cond_indices, class_counts, coverage, accuracy, quality = best_rule_info
        
        # Build Rule object
        conditions = []
        for idx in cond_indices:
            feat_idx, op, val, is_num = self._feature_conditions[idx]
            feat_name = self.feature_names_[feat_idx]
            conditions.append(Condition(feat_name, op, val, is_num))
        
        # Get predicted class and distribution
        majority_idx = class_counts.argmax()
        predicted_class = self.classes_[majority_idx]
        class_distribution = {self.classes_[i]: int(class_counts[i]) 
                            for i in range(len(self.classes_)) if class_counts[i] > 0}
        
        rule = Rule(
            conditions=conditions,
            predicted_class=predicted_class,
            coverage=int(coverage),
            accuracy=accuracy,
            class_distribution=class_distribution,
            quality_score=quality
        )
        rule._condition_indices = cond_indices  # Store for mask computation
        
        return rule
    
    def _compute_quality_fast(self, class_counts: np.ndarray, coverage: int, total: int) -> float:
        """Compute quality score efficiently using numpy."""
        if coverage == 0 or total == 0:
            return float('-inf')
        
        try:
            if self.quality_measure == 'likelihood_ratio':
                # Likelihood ratio
                n_classes = len(self.classes_)
                if n_classes == 0:
                    return float('-inf')
                expected = coverage / n_classes
                if expected <= 0:
                    return float('-inf')
                lr = 0.0
                for count in class_counts:
                    if count > 0:
                        lr += count * np.log(count / expected + 1e-10)
                result = 2 * lr
            else:
                # Entropy-based
                probs = class_counts / coverage
                probs = probs[probs > 0]
                if len(probs) == 0:
                    return float('-inf')
                entropy = -np.sum(probs * np.log2(probs + 1e-10))
                max_entropy = np.log2(len(self.classes_))
                if max_entropy > 0:
                    entropy /= max_entropy
                result = (coverage / total) * (1.0 - entropy)
            
            # Guard against NaN
            if np.isnan(result) or np.isinf(result):
                return float('-inf')
            return float(result)
        except Exception:
            return float('-inf')
    
    def predict(self, X) -> np.ndarray:
        """
        Predict class labels for samples in X.
        """
        self._check_is_fitted()
        X = self._ensure_dataframe(X)
        
        predictions = np.full(len(X), self.default_class_, dtype=object)
        predicted = np.zeros(len(X), dtype=bool)
        
        for rule in self.rules_:
            mask = rule.covers_mask(X)
            new_preds = mask & ~predicted
            predictions[new_preds] = rule.predicted_class
            predicted |= mask
        
        return predictions
    
    def predict_proba(self, X) -> np.ndarray:
        """
        Return class probability estimates for samples in X.
        """
        self._check_is_fitted()
        X = self._ensure_dataframe(X)
        
        n_samples = len(X)
        n_classes = len(self.classes_)
        proba = np.zeros((n_samples, n_classes))
        
        # Default probabilities
        default_proba = self._compute_proba_from_distribution(
            Counter({c: 1 for c in self.classes_})
        )
        
        assigned = np.zeros(n_samples, dtype=bool)
        
        for rule in self.rules_:
            mask = rule.covers_mask(X)
            new_assignments = mask & ~assigned
            
            if new_assignments.sum() > 0:
                rule_proba = self._compute_proba_from_distribution(rule.class_distribution)
                proba[new_assignments] = rule_proba
                assigned[new_assignments] = True
        
        proba[~assigned] = default_proba
        return proba
    
    def _compute_proba_from_distribution(self, class_dist: Dict[Any, int]) -> np.ndarray:
        """Compute class probabilities from distribution."""
        n_classes = len(self.classes_)
        proba = np.zeros(n_classes)
        total = sum(class_dist.values())
        
        if self.laplace_smoothing:
            smoothed_total = total + n_classes
            for i, cls in enumerate(self.classes_):
                count = class_dist.get(cls, 0)
                proba[i] = (count + 1) / smoothed_total
        else:
            for i, cls in enumerate(self.classes_):
                count = class_dist.get(cls, 0)
                proba[i] = count / total if total > 0 else 1 / n_classes
        
        return proba
    
    def get_rules(self) -> List[Rule]:
        """Return the learned rules."""
        self._check_is_fitted()
        return self.rules_.copy()
    
    def get_rules_as_df(self) -> pd.DataFrame:
        """Return rules as a pandas DataFrame."""
        self._check_is_fitted()
        records = []
        for i, rule in enumerate(self.rules_):
            records.append({
                'rule_id': i + 1,
                'conditions': ' AND '.join(str(c) for c in rule.conditions) or 'True',
                'predicted_class': rule.predicted_class,
                'coverage': rule.coverage,
                'accuracy': rule.accuracy,
                'quality_score': rule.quality_score,
                'n_conditions': len(rule.conditions)
            })
        return pd.DataFrame(records)
    
    def score(self, X, y) -> float:
        """Return accuracy on test data."""
        predictions = self.predict(X)
        return np.mean(predictions == np.asarray(y))
    
    def _validate_input(self, X, y) -> Tuple[pd.DataFrame, np.ndarray]:
        """Validate and convert input data."""
        X = self._ensure_dataframe(X)
        y = np.asarray(y, dtype=object)  # Keep as object to preserve types
        
        if len(X) != len(y):
            raise ValueError(f"X and y must have same length. Got {len(X)} and {len(y)}")
        
        if len(X) == 0:
            raise ValueError("Cannot fit on empty dataset")
        
        # Handle NaN values in target - remove rows with NaN target
        # Check for NaN: works for float NaN and None
        valid_mask = np.array([
            not (v is None or (isinstance(v, float) and np.isnan(v)) or 
                 (isinstance(v, str) and v.lower() == 'nan') or
                 pd.isna(v))
            for v in y
        ])
        
        if valid_mask.sum() == 0:
            raise ValueError("All target values are NaN or missing")
        
        if valid_mask.sum() < len(y):
            # Filter out rows with NaN target
            X = X.loc[valid_mask].reset_index(drop=True)
            y = y[valid_mask]
        
        # Convert target to string to avoid mixed type issues during np.unique
        y = np.array([str(v) for v in y])
        
        return X, y
    
    def _ensure_dataframe(self, X) -> pd.DataFrame:
        """Convert X to DataFrame."""
        if isinstance(X, pd.DataFrame):
            return X.copy()
        elif isinstance(X, np.ndarray):
            return pd.DataFrame(X, columns=[f"feature_{i}" for i in range(X.shape[1])])
        else:
            raise TypeError(f"X must be DataFrame or ndarray, got {type(X)}")
    
    def _check_is_fitted(self):
        """Check if fitted."""
        if not self._is_fitted:
            raise RuntimeError("CN2Classifier not fitted. Call fit() first.")


# =============================================================================
# Visualization (PyQt6)
# =============================================================================

from PyQt6.QtWidgets import (
    QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, 
    QTableWidget, QTableWidgetItem, QLabel, QPushButton,
    QComboBox, QSplitter, QTabWidget, QScrollArea,
    QFrame, QHeaderView, QTextEdit, QSpinBox,
    QDoubleSpinBox, QGroupBox, QFormLayout, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor


class CN2RulesVisualization(QMainWindow):
    """
    Window to visualize CN2 classification rules.
    """
    
    rulesApplied = pyqtSignal(object)
    
    def __init__(
        self, 
        classifier: CN2Classifier, 
        X: pd.DataFrame,
        y: np.ndarray,
        target_column: str = "target",
        parent=None
    ):
        super().__init__(parent)
        self.classifier = classifier
        self.X = X
        self.y = y
        self.target_column = target_column
        
        self.setWindowTitle(f"CN2 Rule Induction - {target_column}")
        self.setGeometry(100, 100, 1200, 800)
        
        self._setup_ui()
        self._populate_data()
    
    def _setup_ui(self):
        """Set up the user interface."""
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        
        # Title
        title_label = QLabel(f"CN2 Rule Induction Analysis: {self.target_column}")
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(14)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title_label)
        
        # Description
        desc_label = QLabel(
            "CN2 learns interpretable IF-THEN classification rules. "
            "Rules are applied in order - the first matching rule determines the prediction."
        )
        desc_label.setWordWrap(True)
        main_layout.addWidget(desc_label)
        
        # Summary stats
        self._create_summary_section(main_layout)
        
        # Tabs
        tab_widget = QTabWidget()
        
        # Rules Table Tab
        rules_tab = QWidget()
        rules_layout = QVBoxLayout(rules_tab)
        self.rules_table = self._create_rules_table()
        rules_layout.addWidget(self.rules_table)
        tab_widget.addTab(rules_tab, "Rules")
        
        # Rule Details Tab
        details_tab = QWidget()
        details_layout = QVBoxLayout(details_tab)
        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        self.details_text.setFont(QFont("Courier New", 10))
        details_layout.addWidget(self.details_text)
        tab_widget.addTab(details_tab, "Rule Details")
        
        # Algorithm Info Tab
        info_tab = QWidget()
        info_layout = QVBoxLayout(info_tab)
        self.info_text = QTextEdit()
        self.info_text.setReadOnly(True)
        info_layout.addWidget(self.info_text)
        tab_widget.addTab(info_tab, "Algorithm Info")
        
        main_layout.addWidget(tab_widget, 1)
        
        # Apply button
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.apply_button = QPushButton("Apply Rules")
        self.apply_button.setStyleSheet("""
            QPushButton {
                background-color: #3498DB;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #2980B9; }
        """)
        self.apply_button.clicked.connect(self._apply_rules)
        button_layout.addWidget(self.apply_button)
        
        main_layout.addLayout(button_layout)
    
    def _create_summary_section(self, parent_layout):
        """Create summary statistics section."""
        summary_frame = QFrame()
        summary_frame.setFrameShape(QFrame.Shape.StyledPanel)
        summary_layout = QHBoxLayout(summary_frame)
        
        self.n_rules_label = QLabel("Rules: -")
        self.n_rules_label.setStyleSheet("font-weight: bold;")
        summary_layout.addWidget(self.n_rules_label)
        
        summary_layout.addWidget(QLabel("|"))
        
        self.accuracy_label = QLabel("Training Accuracy: -")
        self.accuracy_label.setStyleSheet("font-weight: bold;")
        summary_layout.addWidget(self.accuracy_label)
        
        summary_layout.addWidget(QLabel("|"))
        
        self.coverage_label = QLabel("Total Coverage: -")
        self.coverage_label.setStyleSheet("font-weight: bold;")
        summary_layout.addWidget(self.coverage_label)
        
        summary_layout.addWidget(QLabel("|"))
        
        self.classes_label = QLabel("Classes: -")
        summary_layout.addWidget(self.classes_label)
        
        summary_layout.addStretch()
        parent_layout.addWidget(summary_frame)
    
    def _create_rules_table(self) -> QTableWidget:
        """Create rules table widget."""
        table = QTableWidget()
        table.setColumnCount(6)
        table.setHorizontalHeaderLabels([
            "Rule #", "Conditions", "Predicted Class", 
            "Coverage", "Accuracy", "Quality"
        ])
        
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        
        table.setColumnWidth(0, 60)
        table.setColumnWidth(2, 120)
        table.setColumnWidth(3, 80)
        table.setColumnWidth(4, 80)
        table.setColumnWidth(5, 80)
        
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.itemSelectionChanged.connect(self._on_rule_selected)
        
        return table
    
    def _populate_data(self):
        """Populate visualization with classifier data."""
        rules = self.classifier.get_rules()
        
        self.n_rules_label.setText(f"Rules: {len(rules)}")
        
        accuracy = self.classifier.score(self.X, self.y)
        self.accuracy_label.setText(f"Training Accuracy: {accuracy:.1%}")
        
        total_coverage = sum(r.coverage for r in rules)
        self.coverage_label.setText(f"Total Coverage: {total_coverage}")
        
        classes_str = ", ".join(str(c) for c in self.classifier.classes_)
        self.classes_label.setText(f"Classes: {classes_str}")
        
        # Populate rules table
        self.rules_table.setRowCount(len(rules))
        for i, rule in enumerate(rules):
            self.rules_table.setItem(i, 0, QTableWidgetItem(str(i + 1)))
            
            conditions_str = " AND ".join(str(c) for c in rule.conditions) or "True"
            self.rules_table.setItem(i, 1, QTableWidgetItem(conditions_str))
            
            self.rules_table.setItem(i, 2, QTableWidgetItem(str(rule.predicted_class)))
            self.rules_table.setItem(i, 3, QTableWidgetItem(str(rule.coverage)))
            self.rules_table.setItem(i, 4, QTableWidgetItem(f"{rule.accuracy:.1%}"))
            self.rules_table.setItem(i, 5, QTableWidgetItem(f"{rule.quality_score:.2f}"))
            
            # Color by accuracy
            if rule.accuracy >= 0.9:
                color = QColor(200, 255, 200)
            elif rule.accuracy >= 0.7:
                color = QColor(255, 255, 200)
            else:
                color = QColor(255, 200, 200)
            
            for j in range(6):
                item = self.rules_table.item(i, j)
                if item:
                    item.setBackground(color)
        
        self._populate_algorithm_info()
        
        if rules:
            self.rules_table.selectRow(0)
    
    def _populate_algorithm_info(self):
        """Populate algorithm info tab."""
        clf = self.classifier
        info = f"""
=== CN2 Rule Induction Algorithm ===

Parameters:
  • Beam Width: {clf.beam_width}
  • Min Covered Examples: {clf.min_covered_examples}
  • Max Rule Length: {clf.max_rule_length}
  • Max Rules: {clf.max_rules}
  • Quality Measure: {clf.quality_measure}
  • Discretization Bins: {clf.discretization_bins}

Dataset:
  • Total Samples: {len(self.X)}
  • Features: {clf.n_features_}
  • Classes: {len(clf.classes_)}

Results:
  • Rules Learned: {len(clf.rules_)}
  • Default Class: {clf.default_class_}
  • Training Accuracy: {clf.score(self.X, self.y):.2%}

How CN2 Works:
1. Pre-compute all possible condition masks (for speed)
2. Use beam search to find the best rule
3. Add rule to rule list
4. Remove covered examples
5. Repeat until stopping criteria met
"""
        self.info_text.setPlainText(info)
    
    def _on_rule_selected(self):
        """Handle rule selection."""
        selected = self.rules_table.selectedItems()
        if not selected:
            return
        
        row = selected[0].row()
        rules = self.classifier.get_rules()
        if row < len(rules):
            self._show_rule_details(rules[row], row + 1)
    
    def _show_rule_details(self, rule: Rule, rule_num: int):
        """Show rule details."""
        details = f"""
=== Rule {rule_num} Details ===

Full Rule:
  {str(rule)}

Conditions ({len(rule.conditions)}):
"""
        if rule.conditions:
            for i, cond in enumerate(rule.conditions, 1):
                details += f"  {i}. {cond}\n"
        else:
            details += "  (No conditions - default rule)\n"
        
        details += f"""
Prediction:
  Predicted Class: {rule.predicted_class}

Metrics:
  Coverage: {rule.coverage} examples
  Accuracy: {rule.accuracy:.2%}
  Quality Score: {rule.quality_score:.4f}

Class Distribution:
"""
        for cls, count in sorted(rule.class_distribution.items(), key=lambda x: -x[1]):
            pct = count / rule.coverage * 100 if rule.coverage > 0 else 0
            bar = "█" * int(pct / 5)
            details += f"  {cls}: {count} ({pct:.1f}%) {bar}\n"
        
        self.details_text.setPlainText(details)
    
    def _apply_rules(self):
        """Apply rules."""
        reply = QMessageBox.question(
            self,
            "Apply Rules",
            "Apply these rules to generate predictions?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.rulesApplied.emit(self.classifier)
            QMessageBox.information(self, "Rules Applied", "CN2 classifier applied successfully.")


# =============================================================================
# Convenience Functions
# =============================================================================

def fit_cn2(df: pd.DataFrame, target_column: str, **kwargs) -> CN2Classifier:
    """
    Fit a CN2 classifier on a DataFrame.
    """
    if target_column not in df.columns:
        raise ValueError(f"Target column '{target_column}' not found")
    
    X = df.drop(columns=[target_column])
    y = df[target_column].values
    
    clf = CN2Classifier(**kwargs)
    clf.fit(X, y)
    
    return clf


def visualize_cn2_rules(df: pd.DataFrame, target_column: str, **kwargs) -> CN2RulesVisualization:
    """
    Fit CN2 and create visualization window.
    """
    if target_column not in df.columns:
        raise ValueError(f"Target column '{target_column}' not found")
    
    X = df.drop(columns=[target_column])
    y = df[target_column].values
    
    clf = CN2Classifier(**kwargs)
    clf.fit(X, y)
    
    vis = CN2RulesVisualization(clf, X, y, target_column)
    vis.show()
    
    return vis


# =============================================================================
# Testing
# =============================================================================

def test_cn2():
    """Test the CN2 classifier."""
    print("\n===== Testing CN2 Rule Induction =====\n")
    
    np.random.seed(42)
    n_samples = 150
    
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
    
    df = pd.DataFrame(data)
    
    print("Dataset shape:", df.shape)
    print("Class distribution:")
    print(df['species'].value_counts())
    print()
    
    import time
    start = time.time()
    clf = fit_cn2(df, target_column='species', beam_width=3, min_covered_examples=5)
    elapsed = time.time() - start
    
    rules = clf.get_rules()
    print(f"\nLearned {len(rules)} rules in {elapsed:.3f}s:\n")
    for i, rule in enumerate(rules, 1):
        print(f"Rule {i}: {rule}")
    
    X = df.drop(columns=['species'])
    y = df['species'].values
    
    accuracy = clf.score(X, y)
    print(f"\nTraining accuracy: {accuracy:.2%}")
    
    print("\n===== CN2 Test Complete =====\n")


if __name__ == "__main__":
    test_cn2()
