from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI
from pydantic import BaseModel
from datetime import datetime

from engine import FraudEngine


# --------------------------------------------------
# FASTAPI APP
# --------------------------------------------------

app = FastAPI(
    title="Sentinel Fraud Detection API",
    description="Real-time fraud detection prototype",
    version="1.0"
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------------------------------------------------
# FRAUD ENGINE
# --------------------------------------------------

engine = FraudEngine()


# --------------------------------------------------
# TEMPORARY DATABASE
# --------------------------------------------------
# For now we use memory.
# Later Person 2 can connect SQLite/database.

transactions = []


# --------------------------------------------------
# INPUT FORMAT
# --------------------------------------------------

class Transaction(BaseModel):

    transaction_id: str
    user_id: str

    amount: float

    latitude: float
    longitude: float

    timestamp: datetime | None = None


# --------------------------------------------------
# HOME
# --------------------------------------------------

@app.get("/")
def home():

    return {
        "message": "Sentinel Fraud Detection API is running!"
    }


# --------------------------------------------------
# CREATE TRANSACTION
# --------------------------------------------------

@app.post("/transactions")
def create_transaction(transaction: Transaction):

    data = transaction.model_dump()

    # If timestamp isn't provided,
    # use current time.
    if data["timestamp"] is None:
        data["timestamp"] = datetime.now()

    # Run fraud detection
    result = engine.analyze(
        data,
        transactions
    )

    # Save transaction with fraud analysis results
    data["risk_score"] = result["risk_score"]
    data["risk_level"] = result["risk_level"]
    data["rules"] = result["rules"]

    transactions.append(data)

    return {
        "transaction_id": data["transaction_id"],
        "user_id": data["user_id"],
        "amount": data["amount"],

        "risk_score": result["risk_score"],
        "risk_level": result["risk_level"],

        "rules": result["rules"]
    }


# --------------------------------------------------
# VIEW TRANSACTIONS
# --------------------------------------------------

@app.get("/transactions")
def get_transactions():

    return transactions
