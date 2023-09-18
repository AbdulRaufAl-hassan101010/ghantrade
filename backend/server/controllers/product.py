from flask import request, jsonify
from server.models import Product
from server import db
from server.apis.utils import serialize
from sqlalchemy import desc, asc, or_

def add_product():
    try:
        # get json data from client
        form_data = request.get_json()
        name = form_data.get('name')
        description = form_data.get('description')
        price = form_data.get('price')
        category_id = form_data.get('category_id')

        # validate and refine data
        # save to database
        product = Product(name=name,description=description, price=price, category_id=category_id)
        db.session.add(product)
        db.session.commit()

        serialized_data = serialize(product)
        return jsonify(serialized_data), 201

    except Exception as error:
        print(error)
        return "add product error"
    

def get_products(id=None):
    try:
        # Retrieve query parameters from the request URL
        id = request.args.get('id', None, type=int)
        order = request.args.get('order', 'desc')
        order_column = request.args.get('order_column', 'created_at')
        search = request.args.get('search', None)

        # Create the base query for the Product table
        query = Product.query

        # Filter by 'id' if provided
        if id is not None:
            query = query.filter_by(product_id=id)


        # Apply search filter if 'search_term' is provided
        if search is not None:
            # Use 'ilike' to perform a case-insensitive search on the 'name' column
            query = query.filter(Product.name.ilike(f"%{search}%"))
            print(len(search), search)

         # Determine the sorting order based on 'order'
        if order == 'desc':
            query = query.order_by(desc(getattr(Product, order_column)))
        else:
            query = query.order_by(asc(getattr(Product, order_column)))

        # Execute the query and retrieve the results
        products = query.all()
        if products is None:
            return jsonify({"error": "Product not found"}), 404

        if len(products) < 1:
            return [], 200
        
        serialized_data = serialize(products)

        if id:
         return jsonify(serialized_data[0]), 200

        return jsonify(serialized_data), 200

    except Exception as error:
        print(error)
        return jsonify({"error": "Failed to retrieve products"}), 500
    

def update_product(id):
    try:
        # Retrieve the existing product by id
        product = Product.query.get(id)

        # Check if the product exists
        if product is None:
            return jsonify({"error": "Product not found"}), 404

        # Extract the new name from the request JSON data
        data = request.get_json()
        new_name = data.get('name')

        # Update the name field if a new name is provided
        if new_name is not None:
            product.name = new_name

            # Commit the changes to the database
            db.session.commit()

            # Serialize and return the updated product
            serialized_data = serialize(product)
            return jsonify(serialized_data), 200
        else:
            return jsonify({"error": "Invalid or missing 'name' field in the request"}), 400

    except Exception as error:
        print(error)
        return jsonify({"error": "Failed to update product"}), 500