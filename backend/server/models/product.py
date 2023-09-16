from server import db
from datetime import datetime

class Product(db.Model):
    __tablename__ = 'products'

    product_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    price = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=0)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.cat_id'), nullable=True)

    # Define a relationship to access the Category model
    category = db.relationship('Category', backref=db.backref('products', lazy=True))

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __init__(self, name, description, price, quantity=0, category_id=None):
        self.name = name
        self.description = description
        self.price = price
        self.quantity = quantity
        self.category_id = category_id

    def __repr__(self):
        return f'<Product {self.product_id}: {self.name}>'