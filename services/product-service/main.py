"""Product Service - Example microservice for product management."""
from datetime import datetime
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel


# Product models
class Product(BaseModel):
    id: Optional[int] = None
    name: str
    description: str
    price: float
    stock: int
    category: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ProductCreate(BaseModel):
    name: str
    description: str
    price: float
    stock: int
    category: str


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    stock: Optional[int] = None
    category: Optional[str] = None


# Create FastAPI app
app = FastAPI(
    title="Product Service",
    version="1.0.0",
    description="Product catalog microservice",
)

# In-memory database (for demo purposes)
products_db = {
    1: Product(
        id=1,
        name="Laptop",
        description="High-performance laptop",
        price=999.99,
        stock=50,
        category="Electronics",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    ),
    2: Product(
        id=2,
        name="Wireless Mouse",
        description="Ergonomic wireless mouse",
        price=29.99,
        stock=200,
        category="Electronics",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    ),
    3: Product(
        id=3,
        name="Office Chair",
        description="Comfortable office chair",
        price=199.99,
        stock=75,
        category="Furniture",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    ),
}

next_product_id = 4


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "product-service"}


@app.get("/api/products", response_model=List[Product])
async def list_products(
    category: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
):
    """List all products with optional filters."""
    products = list(products_db.values())

    # Apply filters
    if category:
        products = [p for p in products if p.category.lower() == category.lower()]

    if min_price is not None:
        products = [p for p in products if p.price >= min_price]

    if max_price is not None:
        products = [p for p in products if p.price <= max_price]

    return products


@app.get("/api/products/{product_id}", response_model=Product)
async def get_product(product_id: int):
    """Get product by ID."""
    product = products_db.get(product_id)

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    return product


@app.post("/api/products", response_model=Product)
async def create_product(product_data: ProductCreate):
    """Create a new product."""
    global next_product_id

    new_product = Product(
        id=next_product_id,
        name=product_data.name,
        description=product_data.description,
        price=product_data.price,
        stock=product_data.stock,
        category=product_data.category,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    products_db[next_product_id] = new_product
    next_product_id += 1

    return new_product


@app.put("/api/products/{product_id}", response_model=Product)
async def update_product(product_id: int, product_data: ProductUpdate):
    """Update a product."""
    product = products_db.get(product_id)

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    if product_data.name is not None:
        product.name = product_data.name
    if product_data.description is not None:
        product.description = product_data.description
    if product_data.price is not None:
        product.price = product_data.price
    if product_data.stock is not None:
        product.stock = product_data.stock
    if product_data.category is not None:
        product.category = product_data.category

    product.updated_at = datetime.utcnow()

    return product


@app.delete("/api/products/{product_id}")
async def delete_product(product_id: int):
    """Delete a product."""
    if product_id not in products_db:
        raise HTTPException(status_code=404, detail="Product not found")

    del products_db[product_id]

    return {"message": "Product deleted successfully"}


@app.get("/api/products/{product_id}/stock")
async def get_product_stock(product_id: int):
    """Get product stock level."""
    product = products_db.get(product_id)

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    return {
        "product_id": product_id,
        "name": product.name,
        "stock": product.stock,
        "in_stock": product.stock > 0,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8002, reload=True)
