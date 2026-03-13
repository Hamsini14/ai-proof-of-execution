"""
AI Engine: Loads the trained Random Forest model and runs predictions.
Implements:
  - Stage 2: Behavioral Consistency Fingerprinting
  - Stage 3: AI Decision Execution
"""
import os
import json
from typing import Dict, Any, Tuple

import numpy as np
import pandas as pd  # pyre-ignore[21]
import joblib  # pyre-ignore[21]

FEATURES = ["credit_score", "income", "loan_amount", "existing_debt",
            "employment_status", "loan_term"]

EMPLOYMENT_MAP = {"employed": 0, "self_employed": 1, "unemployed": 2}

MODEL_VERSION = "LoanModel_RF_v1.0"

def _load_model():
    model_path = os.path.join(os.path.dirname(__file__), "loan_model.pkl")
    if not os.path.exists(model_path):
        raise RuntimeError(
            "Loan model not found. Run: python -m backend.train_model"
        )
    return joblib.load(model_path)

_model = None

def get_model():
    global _model
    if _model is None:
        _model = _load_model()
    return _model


def _input_to_features(input_data: Dict[str, Any]) -> pd.DataFrame:
    """Convert raw input dict to the model's feature DataFrame."""
    employment_raw = str(input_data.get("employment_status", "employed")).lower()
    employment_encoded = EMPLOYMENT_MAP.get(employment_raw, 0)

    row = {
        "credit_score": int(input_data.get("credit_score", 650)),
        "income": float(input_data.get("income", 50000)),
        "loan_amount": float(input_data.get("loan_amount", 10000)),
        "existing_debt": float(input_data.get("existing_debt", 5000)),
        "employment_status": employment_encoded,
        "loan_term": int(input_data.get("loan_term", 36)),
    }
    return pd.DataFrame([row], columns=FEATURES)


def _predict(input_data: Dict[str, Any]) -> Tuple[str, float]:
    """Run model inference and return (decision_label, confidence)."""
    model = get_model()
    X = _input_to_features(input_data)
    proba = model.predict_proba(X)[0]  # [prob_reject, prob_approve]
    pred_class = int(np.argmax(proba))
    confidence = float(proba[pred_class])
    decision = "Loan Approved" if pred_class == 1 else "Loan Rejected"
    return str(decision), float(round(float(proba[pred_class]), 4))


def check_behavioral_consistency(input_data: Dict[str, Any]) -> bool:
    """
    Stage 2: Behavioral Consistency Fingerprinting.
    Perturbs credit_score slightly and checks that the model does not flip.
    """
    base_decision, _ = _predict(input_data)

    perturbed = [
        {**input_data, "credit_score": input_data.get("credit_score", 650) - 2},
        {**input_data, "credit_score": input_data.get("credit_score", 650) + 2},
        {**input_data, "income": input_data.get("income", 50000) - 500},
        {**input_data, "income": input_data.get("income", 50000) + 500},
    ]

    for variant in perturbed:
        v_decision, _ = _predict(variant)
        if v_decision != base_decision:
            print(f"⚠ Behavioral Instability: base={base_decision}, variant={v_decision}")
            return False

    return True


def execute_decision(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Stage 3: Execute the actual AI decision.
    Returns result dict compatible with accountability pipeline.
    """
    decision, confidence = _predict(input_data)
    return {
        "model_version": MODEL_VERSION,
        "decision": decision,
        "confidence": confidence,
    }
