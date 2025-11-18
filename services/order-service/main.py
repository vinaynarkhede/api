"""Order Service - Example microservice for order management."""
from datetime import datetime
from typing import List, Optional
from enum import Enum
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel


# Enums
class OrderStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


# Order models
class OrderItem(BaseModel):
    product_id: int
    product_name: str
    quantity: int
    price: float


class Order(BaseModel):
    id: Optional[int] = None
    user_id: int
    items: List[OrderItem]
    total_amount: float
    status: OrderStatus = OrderStatus.PENDING
    shipping_address: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class OrderCreate(BaseModel):
    user_id: int
    items: List[OrderItem]
    shipping_address: str


class OrderUpdate(BaseModel):
    status: Optional[OrderStatus] = None
    shipping_address: Optional[str] = None


# Create FastAPI app
app = FastAPI(
    title="Order Service",
    version="1.0.0",
    description="Order management microservice",
)

# In-memory database (for demo purposes)
orders_db = {
    1: Order(
        id=1,
        user_id=1,
        items=[
            OrderItem(product_id=1, product_name="Laptop", quantity=1, price=999.99),
            OrderItem(product_id=2, product_name="Wireless Mouse", quantity=2, price=29.99),
        ],
        total_amount=1059.97,
        status=OrderStatus.DELIVERED,
        shipping_address="123 Main St, City, State 12345",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    ),
    2: Order(
        id=2,
        user_id=2,
        items=[
            OrderItem(product_id=3, product_name="Office Chair", quantity=1, price=199.99),
        ],
        total_amount=199.99,
        status=OrderStatus.PROCESSING,
        shipping_address="456 Oak Ave, City, State 67890",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    ),
}

next_order_id = 3


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "order-service"}


@app.get("/api/orders", response_model=List[Order])
async def list_orders(
    user_id: Optional[int] = None,
    status: Optional[OrderStatus] = None,
):
    """List all orders with optional filters."""
    orders = list(orders_db.values())

    # Apply filters
    if user_id is not None:
        orders = [o for o in orders if o.user_id == user_id]

    if status is not None:
        orders = [o for o in orders if o.status == status]

    return orders


@app.get("/api/orders/{order_id}", response_model=Order)
async def get_order(order_id: int):
    """Get order by ID."""
    order = orders_db.get(order_id)

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    return order


@app.post("/api/orders", response_model=Order)
async def create_order(order_data: OrderCreate):
    """Create a new order."""
    global next_order_id

    # Calculate total amount
    total_amount = sum(item.price * item.quantity for item in order_data.items)

    new_order = Order(
        id=next_order_id,
        user_id=order_data.user_id,
        items=order_data.items,
        total_amount=total_amount,
        status=OrderStatus.PENDING,
        shipping_address=order_data.shipping_address,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    orders_db[next_order_id] = new_order
    next_order_id += 1

    return new_order


@app.put("/api/orders/{order_id}", response_model=Order)
async def update_order(order_id: int, order_data: OrderUpdate):
    """Update an order."""
    order = orders_db.get(order_id)

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order_data.status is not None:
        order.status = order_data.status

    if order_data.shipping_address is not None:
        order.shipping_address = order_data.shipping_address

    order.updated_at = datetime.utcnow()

    return order


@app.delete("/api/orders/{order_id}")
async def cancel_order(order_id: int):
    """Cancel an order."""
    order = orders_db.get(order_id)

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Can only cancel pending or processing orders
    if order.status in [OrderStatus.SHIPPED, OrderStatus.DELIVERED]:
        raise HTTPException(
            status_code=400,
            detail="Cannot cancel order that is already shipped or delivered"
        )

    order.status = OrderStatus.CANCELLED
    order.updated_at = datetime.utcnow()

    return {"message": "Order cancelled successfully", "order": order}


@app.get("/api/orders/{order_id}/status")
async def get_order_status(order_id: int):
    """Get order status."""
    order = orders_db.get(order_id)

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    return {
        "order_id": order_id,
        "status": order.status,
        "updated_at": order.updated_at,
    }


@app.post("/api/orders/{order_id}/ship")
async def ship_order(order_id: int):
    """Mark order as shipped."""
    order = orders_db.get(order_id)

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.status != OrderStatus.PROCESSING:
        raise HTTPException(
            status_code=400,
            detail="Can only ship orders that are being processed"
        )

    order.status = OrderStatus.SHIPPED
    order.updated_at = datetime.utcnow()

    return {"message": "Order marked as shipped", "order": order}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8003, reload=True)
