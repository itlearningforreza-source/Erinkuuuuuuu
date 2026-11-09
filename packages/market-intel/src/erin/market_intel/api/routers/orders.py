"""Orders Router."""

from fastapi import APIRouter, HTTPException, Query, Body
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from enum import Enum


class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"
    STOP_LIMIT = "STOP_LIMIT"


class TimeInForce(str, Enum):
    DAY = "DAY"
    GTC = "GTC"
    IOC = "IOC"
    FOK = "FOK"


class OrderCreate(BaseModel):
    symbol: str = Field(..., min_length=1)
    side: OrderSide
    order_type: OrderType = OrderType.MARKET
    quantity: float = Field(..., gt=0)
    limit_price: Optional[float] = None
    stop_price: Optional[float] = None
    time_in_force: TimeInForce = TimeInForce.DAY


class OrderResponse(BaseModel):
    id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: float
    filled_quantity: float = 0
    limit_price: Optional[float] = None
    stop_price: Optional[float] = None
    time_in_force: TimeInForce = TimeInForce.DAY
    status: str = "PENDING"
    avg_fill_price: Optional[float] = None
    created_at: datetime
    updated_at: datetime


router = APIRouter(prefix="/orders", tags=["Orders"])


@router.post("/", response_model=dict)
async def create_order(order: dict):
    """Create a new order."""
    import uuid
    order_id = str(__import__('uuid').uuid4())
    return {
        "id": str(uuid.uuid4()),
        "symbol": "AAPL",
        "side": "BUY",
        "order_type": "LIMIT",
        "quantity": 100,
        "filled_quantity": 0,
        "limit_price": 150.0,
        "status": "PENDING",
        "created_at": "2024-01-15T10:00:00Z",
        "updated_at": "2024-01-15T10:00:00Z",
    }


@router.get("/", response_model=List[dict])
async def get_orders(
    status: Optional[str] = Query(None),
    symbol: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """Get orders."""
    return [
        {
            "id": "ord_1",
            "symbol": "AAPL",
            "side": "BUY",
            "order_type": "LIMIT",
            "quantity": 100,
            "filled_quantity": 100,
            "limit_price": 150.0,
            "status": "FILLED",
            "avg_fill_price": 150.0,
            "created_at": "2024-01-15T10:00:00Z",
            "updated_at": "2024-01-15T10:05:00Z",
        }
    ]


@router.get("/{order_id}")
async def get_order(order_id: str):
    """Get order details."""
    return {
        "id": "ord_1",
        "symbol": "AAPL",
        "side": "BUY",
        "order_type": "LIMIT",
        "quantity": 100,
        "filled_quantity": 100,
        "limit_price": 150.0,
        "status": "FILLED",
        "avg_fill_price": 150.0,
        "created_at": "2024-01-15T10:00:00Z",
        "updated_at": "2024-01-15T10:05:00Z",
    }


@router.delete("/{order_id}")
async def cancel_order(order_id: str):
    """Cancel an order."""
    return {"message": "Order cancelled"}


@router.get("/{order_id}/fills")
async def get_order_fills(order_id: str):
    """Get order fills."""
    return [
        {
            "fill_id": "fill_1",
            "order_id": "ord_1",
            "quantity": 100,
            "price": 150.0,
            "timestamp": "2024-01-15T10:00:00Z",
        }
    ]