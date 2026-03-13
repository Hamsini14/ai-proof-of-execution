import uuid
import time
import datetime
from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks # pyre-ignore[21]
import traceback
from fastapi.middleware.cors import CORSMiddleware # pyre-ignore[21]
from sqlalchemy.orm import Session # pyre-ignore[21]
import pandas as pd
import yfinance as yf
from typing import List, Optional, Dict, Any

from backend import models, database, crypto_utils, ai_engine, stock_engine, blockchain # pyre-ignore[21]
from backend.behavior_detector import analyze_behavior

app = FastAPI(title="AI Accountability Framework", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup_event():
    # Drop old table and recreate with new schema (adds merkle_root + tampered columns)
    database.Base.metadata.drop_all(bind=database.engine)
    database.Base.metadata.create_all(bind=database.engine)

# -----------------------------------------------------------------------
# Background task: runs with its OWN fresh DB session (fixes stale-session bug)
# -----------------------------------------------------------------------
def anchor_and_verify_task(decision_id: str, execution_hash: str):
    """
    Stage 6-7: Build Merkle tree for this single record and anchor to blockchain.
    Stage 11: Auto-verify the record after anchoring.
    Uses a fresh DB session — safe to run in background.
    """
    # Simulate brief blockchain confirmation delay (~1 second)
    time.sleep(1)

    db = database.SessionLocal()
    try:
        record = db.query(database.ExecutionRecordDB).filter(
            database.ExecutionRecordDB.decision_id == decision_id
        ).first()
        if not record:
            return

        # Stage 6: Build Merkle tree (single leaf = the execution hash itself)
        merkle_root = crypto_utils.build_merkle_tree([execution_hash])

        # Stage 7: Anchor to blockchain
        batch_id = f"BATCH_{str(uuid.uuid4()).split('-')[0]}"
        tx_id = blockchain.blockchain_client.anchor_merkle_root(batch_id, merkle_root)

        # Update to "Anchored" (blockchain tx confirmed)
        record.merkle_root = merkle_root
        record.blockchain_tx_id = tx_id
        record.status = "Anchored"
        db.commit()

        # Stage 11: Auto-verify — recompute hash and compare
        # Build the canonical execution record dict (same as when original hash was made)
        # Use a consistent format to avoid mismatch with DB retrieval precision
        ts_str = record.timestamp.strftime("%Y-%m-%dT%H:%M:%S.%f")
        execution_record_dict = {
            "decision_id": str(record.decision_id),
            "input_hash": str(record.input_hash),
            "model_version": str(record.model_version),
            "credit_score": int(record.credit_score),
            "income": float(record.income),
            "loan_amount": float(record.loan_amount),
            "existing_debt": float(record.existing_debt),
            "employment_status": str(record.employment_status),
            "loan_term": int(record.loan_term),
            "decision": str(record.decision),
            "confidence": float(record.confidence),
            "timestamp": ts_str,
        }
        recomputed_hash = crypto_utils.generate_hash(execution_record_dict)

        if recomputed_hash == record.execution_hash:
            record.status = "Verified"
        else:
            # Hash mismatch → tampering detected during auto-verification
            record.status = "Tampering Detected"

        db.commit()
    finally:
        db.close()

def anchor_and_verify_stock_task(decision_id: str, execution_hash: str):
    """
    Stage 6-7: Build Merkle tree for this single record and anchor to blockchain.
    Stage 11: Auto-verify the record after anchoring for Stock.
    """
    time.sleep(1)

    db = database.SessionLocal()
    try:
        record = db.query(database.StockExecutionRecordDB).filter(
            database.StockExecutionRecordDB.decision_id == decision_id
        ).first()
        if not record:
            return

        merkle_root = crypto_utils.build_merkle_tree([execution_hash])
        batch_id = f"STOCK_BATCH_{str(uuid.uuid4()).split('-')[0]}"
        tx_id = blockchain.blockchain_client.anchor_merkle_root(batch_id, merkle_root)

        record.merkle_root = merkle_root
        record.blockchain_tx_id = tx_id
        record.status = "Anchored"
        db.commit()

        ts_str = record.timestamp.strftime("%Y-%m-%dT%H:%M:%S.%f")
        execution_record_dict = {
            "decision_id": str(record.decision_id),
            "input_hash": str(record.input_hash),
            "ticker": str(record.ticker),
            "current_price": float(record.current_price),
            "ma_50": float(record.ma_50),
            "rsi_14": float(record.rsi_14),
            "decision": str(record.decision),
            "confidence": float(record.confidence),
            "timestamp": ts_str,
        }
        recomputed_hash = crypto_utils.generate_hash(execution_record_dict)

        if recomputed_hash == record.execution_hash:
            record.status = "Verified"
        else:
            record.status = "Tampering Detected"

        db.commit()
    finally:
        db.close()


# -----------------------------------------------------------------------
# POST /api/decision  — Safe execution (full accountability pipeline)
# -----------------------------------------------------------------------
@app.post("/api/decision", response_model=models.DecisionResponse)
def execute_ai_decision(
    input_data: models.LoanInput,
    background_tasks: BackgroundTasks,
    db: Session = Depends(database.get_db),
):
    # Stage 9: Circuit Breaker pre-check
    if blockchain.blockchain_client.get_system_status() == "HALTED":
        raise HTTPException(status_code=503, detail="AI System Paused for Manual Review")

    input_dict = input_data.model_dump()

    # Stage 1: Input hash
    input_hash = crypto_utils.generate_hash(input_dict)

    # Stage 2: Behavioral consistency check
    if not ai_engine.check_behavioral_consistency(input_dict):
        blockchain.blockchain_client.halt_system()
        raise HTTPException(status_code=400, detail="Behavioral Instability Detected")

    # Stage 3: AI Decision
    ai_result = ai_engine.execute_decision(input_dict)

    decision_id = f"TXN_{str(uuid.uuid4()).split('-')[0]}"
    timestamp = datetime.datetime.utcnow()

    # Stage 4: Execution record
    # Use consistent format for hashing
    ts_str = timestamp.strftime("%Y-%m-%dT%H:%M:%S.%f")
    execution_record_dict = {
        "decision_id": decision_id,
        "input_hash": input_hash,
        "model_version": ai_result["model_version"],
        "credit_score": input_data.credit_score,
        "income": input_data.income,
        "loan_amount": input_data.loan_amount,
        "existing_debt": input_data.existing_debt,
        "employment_status": input_data.employment_status.value if hasattr(input_data.employment_status, 'value') else str(input_data.employment_status),
        "loan_term": input_data.loan_term,
        "decision": ai_result["decision"],
        "confidence": float(ai_result["confidence"]),
        "timestamp": ts_str,
    }

    # Stage 5: Execution hash
    execution_hash = crypto_utils.generate_hash(execution_record_dict)

    # Stage 8: Store off-chain
    db_record = database.ExecutionRecordDB(
        decision_id=decision_id,
        input_hash=input_hash,
        model_version=ai_result["model_version"],
        credit_score=input_data.credit_score,
        income=input_data.income,
        loan_amount=input_data.loan_amount,
        existing_debt=input_data.existing_debt,
        employment_status=input_data.employment_status.value if hasattr(input_data.employment_status, 'value') else str(input_data.employment_status),
        loan_term=input_data.loan_term,
        decision=ai_result["decision"],
        confidence=ai_result["confidence"],
        timestamp=timestamp,
        execution_hash=execution_hash,
        merkle_root=None,
        blockchain_tx_id="Pending",
        status="Anchoring",
        tampered=False,
    )
    db.add(db_record)
    db.commit()

    # Stages 6-7-11: Anchor + verify in background (fresh DB session)
    background_tasks.add_task(anchor_and_verify_task, decision_id, execution_hash)

    return models.DecisionResponse(
        decision_id=decision_id,
        model_version=ai_result["model_version"],
        decision=ai_result["decision"],
        confidence=ai_result["confidence"],
        input_hash=input_hash,
        execution_hash=execution_hash,
        timestamp=timestamp,
        status="Anchoring",
    )

# -----------------------------------------------------------------------
# POST /api/stock/decision  — Stock Engine execution
# -----------------------------------------------------------------------
@app.post("/api/stock/decision", response_model=models.StockDecisionResponse)
def execute_stock_decision(
    input_data: models.StockInput,
    background_tasks: BackgroundTasks,
    db: Session = Depends(database.get_db),
):
    if blockchain.blockchain_client.get_system_status() == "HALTED":
        raise HTTPException(status_code=503, detail="AI System Paused for Manual Review")

    input_dict = input_data.model_dump()
    input_hash = crypto_utils.generate_hash(input_dict)

    try:
        ai_result = stock_engine.execute_stock_decision(input_data.ticker)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Internal Server Error")

    decision_id = f"STK_{str(uuid.uuid4()).split('-')[0]}"
    timestamp = datetime.datetime.utcnow()

    ts_str = timestamp.strftime("%Y-%m-%dT%H:%M:%S.%f")
    execution_record_dict = {
        "decision_id": decision_id,
        "input_hash": input_hash,
        "ticker": input_data.ticker,
        "current_price": ai_result["current_price"],
        "ma_50": ai_result["ma_50"],
        "rsi_14": ai_result["rsi_14"],
        "decision": ai_result["decision"],
        "confidence": float(ai_result["confidence"]),
        "timestamp": ts_str,
    }

    execution_hash = crypto_utils.generate_hash(execution_record_dict)

    db_record = database.StockExecutionRecordDB(
        decision_id=decision_id,
        input_hash=input_hash,
        ticker=input_data.ticker,
        current_price=ai_result["current_price"],
        ma_50=ai_result["ma_50"],
        rsi_14=ai_result["rsi_14"],
        decision=ai_result["decision"],
        confidence=ai_result["confidence"],
        timestamp=timestamp,
        execution_hash=execution_hash,
        merkle_root=None,
        blockchain_tx_id="Pending",
        status="Anchoring",
        tampered=False,
    )
    db.add(db_record)
    db.commit()

    background_tasks.add_task(anchor_and_verify_stock_task, decision_id, execution_hash)

    return models.StockDecisionResponse(
        decision_id=decision_id,
        ticker=input_data.ticker,
        decision=ai_result["decision"],
        confidence=ai_result["confidence"],
        current_price=ai_result["current_price"],
        ma_50=ai_result["ma_50"],
        rsi_14=ai_result["rsi_14"],
        input_hash=input_hash,
        execution_hash=execution_hash,
        timestamp=timestamp,
        status="Anchoring",
    )



@app.get("/api/stats")
def get_stats(db: Session = Depends(database.get_db)):
    records = db.query(database.ExecutionRecordDB).all()
    
    # Convert DB objects to dicts for behavioral analysis
    records_list = [
        {
            "decision": r.decision,
            "timestamp": r.timestamp
        } for r in records
    ]
    behavior_analysis = analyze_behavior(records_list)
    
    total_applicants = int(len(records))
    if total_applicants == 0:
        return {
            "total_applicants": 0,
            "average_credit_score": 0,
            "loan_approval_rate": 0,
            "credit_score_distribution": [],
            "decisions_over_time": [],
            "behavior_analysis": behavior_analysis
        }

    valid_scores = [int(r.credit_score) for r in records if r.credit_score is not None]
    avg_score = float(sum(valid_scores)) / float(len(valid_scores)) if valid_scores else 0.0
    
    approvals = [r for r in records if r.decision == "Loan Approved"]
    approval_rate = (float(len(approvals)) / float(total_applicants)) * 100.0

    # Credit Score Distribution vs Approval Rate
    dist_ranges = [
        {"name": "<550", "min": 0, "max": 549},
        {"name": "550-650", "min": 550, "max": 650},
        {"name": "650-750", "min": 651, "max": 750},
        {"name": "750+", "min": 751, "max": 999},
    ]

    dist_data = []
    for dr in dist_ranges:
        r_min = int(dr["min"])
        r_max = int(dr["max"])
        r_applicants = [r for r in records if r.credit_score is not None and r_min <= int(r.credit_score) <= r_max]
        r_total = int(len(r_applicants))
        r_approved = int(len([r for r in r_applicants if r.decision == "Loan Approved"]))
        
        calc_rate = (float(r_approved) / float(r_total) * 100.0) if r_total > 0 else 0.0
        dist_data.append({
            "range": str(dr["name"]), 
            "approval_rate": float(round(float(calc_rate), 2))
        })

    # Decisions over time
    time_series = {}
    for rec in records:
        day = str(rec.timestamp.strftime("%Y-%m-%d"))
        time_series[day] = int(time_series.get(day, 0)) + 1
    
    sorted_days = sorted(time_series.keys())
    over_time_data = [{"date": str(d), "decisions": int(time_series[d])} for d in sorted_days]

    return {
        "total_applicants": int(total_applicants),
        "average_credit_score": float(round(float(avg_score), 1)),
        "loan_approval_rate": float(round(float(approval_rate), 1)),
        "credit_score_distribution": dist_data,
        "decisions_over_time": over_time_data,
        "behavior_analysis": behavior_analysis
    }

# -----------------------------------------------------------------------
# GET /api/audits
# -----------------------------------------------------------------------
# -----------------------------------------------------------------------
# POST /api/tamper/{decision_id} — Manual Tamper simulation on existing record
# -----------------------------------------------------------------------
@app.post("/api/tamper/{decision_id}")
def manual_tamper_record(
    decision_id: str, 
    tamper_data: Optional[models.TamperRequest] = None,
    db: Session = Depends(database.get_db)
):
    """
    Demo: Modifies the stored execution record AFTER blockchain anchoring.
    Changes the AI decision in the database — the blockchain hash does NOT change.
    When verify is called next, the recomputed hash will differ from the anchored hash,
    and Tampering Detected status will be set.
    """
    record = db.query(database.ExecutionRecordDB).filter(
        database.ExecutionRecordDB.decision_id == decision_id
    ).first()
    if not record:
        raise HTTPException(status_code=404, detail="Decision not found")

    if record.status == "Anchoring":
        raise HTTPException(status_code=400, detail="Record not yet anchored. Please wait.")

    # Flip or set custom values — blockchain hash is untouched
    original_decision = record.decision
    
    if tamper_data and tamper_data.confidence is not None:
        record.confidence = tamper_data.confidence
    else:
        # Fallback flip logic
        curr_conf = float(record.confidence)
        record.confidence = float(round(float(1.0 - curr_conf), 4))

    # Tamper with input features if provided
    if tamper_data:
        if tamper_data.income is not None: record.income = tamper_data.income
        if tamper_data.loan_amount is not None: record.loan_amount = tamper_data.loan_amount
        if tamper_data.existing_debt is not None: record.existing_debt = tamper_data.existing_debt
        if tamper_data.employment_status is not None: record.employment_status = tamper_data.employment_status
        if tamper_data.loan_term is not None: record.loan_term = tamper_data.loan_term
        
    record.tampered = True
    db.commit()

    return {
        "message": f"Record modified. Original decision was '{original_decision}'. Now shows '{record.decision}'.",
        "new_decision": record.decision,
        "original_decision": original_decision,
        "execution_hash_unchanged": record.execution_hash,
    }

# -----------------------------------------------------------------------
# POST /api/stock/tamper/{decision_id} — Manual Tamper simulation on existing stock record
# -----------------------------------------------------------------------
@app.post("/api/stock/tamper/{decision_id}")
def manual_tamper_stock_record(
    decision_id: str, 
    tamper_data: Optional[models.StockTamperRequest] = None,
    db: Session = Depends(database.get_db)
):
    """
    Demo: Modifies the stored stock execution record AFTER blockchain anchoring.
    Changes the AI decision in the database — the blockchain hash does NOT change.
    When verify is called next, the recomputed hash will differ from the anchored hash,
    and Tampering Detected status will be set.
    """
    record = db.query(database.StockExecutionRecordDB).filter(
        database.StockExecutionRecordDB.decision_id == decision_id
    ).first()
    if not record:
        raise HTTPException(status_code=404, detail="Stock Decision not found")

    if record.status == "Anchoring":
        raise HTTPException(status_code=400, detail="Record not yet anchored. Please wait.")

    original_decision = record.decision
    
    if tamper_data and tamper_data.decision:
        record.decision = tamper_data.decision
    else:
        record.decision = "SELL" if original_decision == "BUY" else "BUY"
    
    if tamper_data and tamper_data.confidence is not None:
        record.confidence = tamper_data.confidence
    else:
        curr_conf = float(record.confidence)
        record.confidence = float(round(float(1.0 - curr_conf), 4))

    if tamper_data:
        if tamper_data.current_price is not None: record.current_price = tamper_data.current_price
        if tamper_data.ma_50 is not None: record.ma_50 = tamper_data.ma_50
        if tamper_data.rsi_14 is not None: record.rsi_14 = tamper_data.rsi_14

    record.tampered = True
    db.commit()

    return {
        "message": f"Stock record modified. Original decision was '{original_decision}'. Now shows '{record.decision}'.",
        "new_decision": record.decision,
        "original_decision": original_decision,
        "execution_hash_unchanged": record.execution_hash,
    }

@app.get("/api/stock/history/{ticker}")
def get_stock_history(ticker: str):
    """
    Fetch historical data for charting in the Analytics tab.
    """
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="120d")
        if hist.empty:
            raise HTTPException(status_code=404, detail="Ticker not found or no data available")
        
        print(f"FETCHING HISTORY FOR: {ticker}")
        # Compute MA50 for the chart overlay
        hist['MA50'] = hist['Close'].rolling(window=50).mean()
        
        # Format for Recharts: list of dicts with date, price, ma
        history_data = []
        for index, row in hist.iterrows():
            history_data.append({
                "date": index.strftime('%Y-%m-%d'),
                "price": float(round(float(row['Close']), 2)),
                "ma50": float(round(float(row['MA50']), 2)) if not pd.isna(row['MA50']) else None
            })
        return history_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/audits", response_model=List[models.AuditRecord])
def get_audits(db: Session = Depends(database.get_db)):
    return db.query(database.ExecutionRecordDB).order_by(
        database.ExecutionRecordDB.timestamp.desc()
    ).all()

@app.get("/api/stock/audits", response_model=List[models.StockAuditRecord])
def get_stock_audits(db: Session = Depends(database.get_db)):
    return db.query(database.StockExecutionRecordDB).order_by(
        database.StockExecutionRecordDB.timestamp.desc()
    ).all()


# -----------------------------------------------------------------------
# POST /api/verify/{decision_id}  — Manual on-demand verification
# -----------------------------------------------------------------------
@app.post("/api/verify/{decision_id}")
def verify_record(decision_id: str, db: Session = Depends(database.get_db)):
    record = db.query(database.ExecutionRecordDB).filter(
        database.ExecutionRecordDB.decision_id == decision_id
    ).first()
    if not record:
        raise HTTPException(status_code=404, detail="Decision not found")

    if record.status == "Anchoring":
        return {
            "result": False,
            "status": "Anchoring",
            "message": "Still anchoring to blockchain. Please wait and try again.",
        }

    # Recompute execution hash from stored fields
    ts_str = record.timestamp.strftime("%Y-%m-%dT%H:%M:%S.%f")
    execution_record_dict = {
        "decision_id": str(record.decision_id),
        "input_hash": str(record.input_hash),
        "model_version": str(record.model_version),
        "credit_score": int(record.credit_score),
        "income": float(record.income),
        "loan_amount": float(record.loan_amount),
        "existing_debt": float(record.existing_debt),
        "employment_status": str(record.employment_status),
        "loan_term": int(record.loan_term),
        "decision": str(record.decision),
        "confidence": float(record.confidence),
        "timestamp": ts_str,
    }
    recomputed_hash = crypto_utils.generate_hash(execution_record_dict)

    # Check off-chain integrity (hash recompute match)
    if recomputed_hash != record.execution_hash:
        record.status = "Tampering Detected"
        db.commit()
        return {
            "result": False,
            "status": "Tampering Detected",
            "message": "TAMPERING DETECTED — execution record was modified after hashing!",
            "stored_hash": record.execution_hash,
            "recomputed_hash": recomputed_hash,
        }

    # Check blockchain anchoring
    tx_data = blockchain.blockchain_client.get_transaction(record.blockchain_tx_id)
    if not tx_data:
        return {
            "result": False,
            "status": "Anchoring",
            "message": "Blockchain transaction not yet confirmed.",
            "recomputed_hash": recomputed_hash,
        }

    # Validate Merkle root stored on blockchain matches what we have
    if tx_data.get("merkle_root") != record.merkle_root:
        record.status = "Tampering Detected"
        db.commit()
        return {
            "result": False,
            "status": "Tampering Detected",
            "message": "Merkle root mismatch — blockchain record does not match.",
            "recomputed_hash": recomputed_hash,
        }

    # All checks passed
    record.status = "Verified"
    db.commit()
    return {
        "result": True,
        "status": "Verified",
        "message": "AI decision authentic. Input and output not altered.",
        "recomputed_hash": recomputed_hash,
        "blockchain_tx": record.blockchain_tx_id,
        "merkle_root": record.merkle_root,
    }


# -----------------------------------------------------------------------
# POST /api/replay/{decision_id}  — Re-run the AI model on stored inputs
# -----------------------------------------------------------------------
@app.post("/api/replay/{decision_id}")
def replay_decision(decision_id: str, db: Session = Depends(database.get_db)):
    record = db.query(database.ExecutionRecordDB).filter(
        database.ExecutionRecordDB.decision_id == decision_id
    ).first()
    if not record:
        raise HTTPException(status_code=404, detail="Decision not found")

    # Reconstruct the original input dictionary from the stored record
    input_dict = {
        "credit_score": int(record.credit_score),
        "income": float(record.income),
        "loan_amount": float(record.loan_amount),
        "existing_debt": float(record.existing_debt),
        "employment_status": str(record.employment_status),
        "loan_term": int(record.loan_term),
    }

    # Re-run the core AI decision logic
    ai_result = ai_engine.execute_decision(input_dict)
    replayed_decision = ai_result["decision"]
    replayed_confidence = ai_result["confidence"]

    # Compare the new result with the stored result
    if replayed_decision == record.decision:
        status_msg = "Decision Verified"
        match = True
    else:
        status_msg = "Model Behavior Changed / Potential Drift"
        match = False

    return {
        "decision_id": decision_id,
        "match": match,
        "status": status_msg,
        "stored_decision": record.decision,
        "replayed_decision": replayed_decision,
        "stored_confidence": record.confidence,
        "replayed_confidence": replayed_confidence,
    }

# -----------------------------------------------------------------------
# POST /api/stock/verify/{decision_id}  — Manual on-demand verification
# -----------------------------------------------------------------------
@app.post("/api/stock/verify/{decision_id}")
def verify_stock_record(decision_id: str, db: Session = Depends(database.get_db)):
    record = db.query(database.StockExecutionRecordDB).filter(
        database.StockExecutionRecordDB.decision_id == decision_id
    ).first()
    if not record:
        raise HTTPException(status_code=404, detail="Decision not found")

    if record.status == "Anchoring":
        return {
            "result": False,
            "status": "Anchoring",
            "message": "Still anchoring to blockchain. Please wait and try again.",
        }

    ts_str = record.timestamp.strftime("%Y-%m-%dT%H:%M:%S.%f")
    execution_record_dict = {
        "decision_id": str(record.decision_id),
        "input_hash": str(record.input_hash),
        "ticker": str(record.ticker),
        "current_price": float(record.current_price),
        "ma_50": float(record.ma_50),
        "rsi_14": float(record.rsi_14),
        "decision": str(record.decision),
        "confidence": float(record.confidence),
        "timestamp": ts_str,
    }
    recomputed_hash = crypto_utils.generate_hash(execution_record_dict)

    if recomputed_hash != record.execution_hash:
        record.status = "Tampering Detected"
        db.commit()
        return {
            "result": False,
            "status": "Tampering Detected",
            "message": "TAMPERING DETECTED — execution record was modified after hashing!",
            "stored_hash": record.execution_hash,
            "recomputed_hash": recomputed_hash,
        }

    tx_data = blockchain.blockchain_client.get_transaction(record.blockchain_tx_id)
    if not tx_data:
        return {
            "result": False,
            "status": "Anchoring",
            "message": "Blockchain transaction not yet confirmed.",
            "recomputed_hash": recomputed_hash,
        }

    if tx_data.get("merkle_root") != record.merkle_root:
        record.status = "Tampering Detected"
        db.commit()
        return {
            "result": False,
            "status": "Tampering Detected",
            "message": "Merkle root mismatch — blockchain record does not match.",
            "recomputed_hash": recomputed_hash,
        }

    record.status = "Verified"
    db.commit()
    return {
        "result": True,
        "status": "Verified",
        "message": "AI decision authentic. Input and output not altered.",
        "recomputed_hash": recomputed_hash,
        "blockchain_tx": record.blockchain_tx_id,
        "merkle_root": record.merkle_root,
    }

# -----------------------------------------------------------------------
# POST /api/stock/replay/{decision_id}  — Re-run the AI model on stored inputs
# -----------------------------------------------------------------------
@app.post("/api/stock/replay/{decision_id}")
def replay_stock_decision(decision_id: str, db: Session = Depends(database.get_db)):
    record = db.query(database.StockExecutionRecordDB).filter(
        database.StockExecutionRecordDB.decision_id == decision_id
    ).first()
    if not record:
        raise HTTPException(status_code=404, detail="Decision not found")

    ai_result = stock_engine.execute_stock_decision_from_indicators(
        record.current_price, record.ma_50, record.rsi_14
    )
    replayed_decision = ai_result["decision"]
    replayed_confidence = ai_result["confidence"]

    if replayed_decision == record.decision:
        status_msg = "Decision Verified"
        match = True
    else:
        status_msg = "Model Behavior Changed / Potential Drift"
        match = False

    return {
        "decision_id": decision_id,
        "match": match,
        "status": status_msg,
        "stored_decision": record.decision,
        "replayed_decision": replayed_decision,
        "stored_confidence": record.confidence,
        "replayed_confidence": replayed_confidence,
    }

# -----------------------------------------------------------------------
# GET /api/system/status
# -----------------------------------------------------------------------
@app.get("/api/system/status")
def system_status():
    return {"status": blockchain.blockchain_client.get_system_status()}
