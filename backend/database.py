from sqlalchemy import create_engine, Column, String, Float, DateTime, Boolean, Integer # pyre-ignore[21]
from sqlalchemy.orm import declarative_base, sessionmaker # pyre-ignore[21]
import datetime

DATABASE_URL = "sqlite:///./execution_records.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class ExecutionRecordDB(Base):
    __tablename__ = "execution_records"

    decision_id     = Column(String, primary_key=True, index=True)
    input_hash      = Column(String, index=True)
    model_version   = Column(String)
    credit_score    = Column(Integer)
    income          = Column(Float)
    loan_amount     = Column(Float)
    existing_debt   = Column(Float)
    employment_status = Column(String)
    loan_term       = Column(Integer)
    decision        = Column(String)
    confidence      = Column(Float)
    timestamp       = Column(DateTime, default=datetime.datetime.utcnow)
    execution_hash  = Column(String, index=True)   # hash of the original execution record
    merkle_root     = Column(String, nullable=True) # Merkle root anchored on blockchain
    blockchain_tx_id = Column(String, default="Pending")
    status          = Column(String, default="Anchoring")  # Anchoring | Anchored | Verified | Tampering Detected
    tampered        = Column(Boolean, default=False)        # True if this record was tampered for demo

class StockExecutionRecordDB(Base):
    __tablename__ = "stock_execution_records"

    decision_id     = Column(String, primary_key=True, index=True)
    ticker          = Column(String, index=True)
    current_price   = Column(Float)
    ma_50           = Column(Float)
    rsi_14          = Column(Float)
    decision        = Column(String) # BUY, SELL, HOLD
    confidence      = Column(Float)
    timestamp       = Column(DateTime, default=datetime.datetime.utcnow)
    execution_hash  = Column(String, index=True)
    merkle_root     = Column(String, nullable=True) 
    blockchain_tx_id = Column(String, default="Pending")
    status          = Column(String, default="Anchoring") 
    tampered        = Column(Boolean, default=False)
    input_hash      = Column(String, index=True)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
