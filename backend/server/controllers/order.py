from flask import jsonify, session, request
from server.models import Order,OrderProducts, Product
from server import db,base_url
from server.apis.utils import serialize
from server.utils import NotFoundError
import uuid
import sqlalchemy.exc
import pymysql.err
from sqlalchemy import desc, asc
from server.apis.cart import delete_user_cart
from server.apis.send_mail import send_email
from server.apis.token import generate_token, remove_token_by_token


def add_order():
    """add order"""    
    try:
        json_data = request.get_json()

        order_id = uuid.uuid4()
        user_id = session.get('user_id')


        if not isinstance(json_data, list):
            return jsonify({"error": "Invalid data format. Expected a list of order products."}), 400

        # Validate and process each item in the list
        valid_order_products = []
        totals = 0


        for item in json_data:
            if not isinstance(item, dict):
                raise ValueError("Invalid data format for an order product. Expected a dictionary.")            
            
            if order_id or item['product_id'] or item['quantity']:           
                product = Product.query.get(item['product_id'])
                
                if product is None:
                    raise NotFoundError({'error': 'Not Found Product', 'message': 'Not Found Product'})
                
                
                order_product = OrderProducts(
                    order_id= order_id,
                    product_id= item['product_id'],
                    price= product.price,
                    quantity= item['quantity']
                )
            else:
                raise ValueError("Invalid data format for an order product. attribute can be product_id, price, quantity.")
            
            # calc totals
            totals += order_product.price * order_product.quantity

            # If validation passes, add the valid order product to the list
            valid_order_products.append(order_product)
        
        # update order totals
        totals = totals

        # ADD ORDER TO VALID LIST
        order = Order(order_id= order_id, user_id=user_id, totals=totals)
        valid_order_products.insert(0, order)

        delete_user_cart()

        db.session.add_all(valid_order_products)
        db.session.commit()


        return jsonify({"message": "Order products added successfully."}), 200
    except (sqlalchemy.exc.SQLAlchemyError, pymysql.err.OperationalError,pymysql.err.IntegrityError) as e:
        # Rollback the transaction in case of a database error
        db.session.rollback()

        response = {
            "error": "Database Error",
            "message": str(e)
        }
        status =500
        
        # Handle the specific error condition, such as duplicate products
        if "Duplicate entry" in str(e):
            response = {
            "error": "Duplicate Products",
            "message": "Duplicate Products"
            }
            status = 400      
        
    except (NotFoundError) as e:
        # Handle custom application-level errors here
        db.session.rollback()
        response = e.error_dict
        status = 404  # Set an appropriate status code for your application

    except Exception as e:
        # Handle other general exceptions here
        db.session.rollback()
        response = {
            "error": "Internal Server Error",
            "message": str(e)
        }
        status = 500

    return jsonify(response), status

    

def get_orders_by_id(order_id=None):
    try:
        order = Order.query.get(order_id)

        if order is None:
            return  jsonify({"error": "Not found", "message": 'order not found'}), 404
        
        serialized_orders = serialize(order.orders)        
        serialized_data = serialize(order)
        return jsonify({**serialized_data, 'orders': serialized_orders, 'count': len(serialized_orders)}), 200
    except ValueError as e:
        return jsonify(e), 400
    except Exception as e:
        return jsonify(str(e)), 500
    

def get_all_orders():
    try:
        # Retrieve query parameters from the request URL
        user_id = request.args.get('user_id', None)
        order_id = request.args.get('order_id', None)
        order_status_id = request.args.get('order_status_id', None)
        order_in = request.args.get('order_in', 'desc')
        order_column = request.args.get('order_column', 'created_at')
        search = request.args.get('search', None)
        limit = request.args.get('limit', None)

        # Create the base query for the Order table
        query = Order.query

        # Filter by 'user_id' if provided
        if user_id is not None:
            query = query.filter_by(user_id=user_id)
        # Filter by 'order_id' if provided
        if order_id is not None:
            query = query.filter_by(order_id=order_id)
        # Filter by 'order_status_id' if provided
        if order_status_id is not None:
            query = query.filter_by(order_status_id=order_status_id)


        # Apply search filter if 'search_term' is provided
        if search is not None:
            if search == '':
                return jsonify([]), 200
            
            # Use 'ilike' to perform a case-insensitive search on the 'name' column
            query = query.filter(Order.order_id.ilike(f"%{search}%"))


        # Determine the sorting order based on 'order'
        print(order_in)
        if order_in == 'desc':
            query = query.order_by(desc(getattr(Order, order_column)))
        else:
            query = query.order_by(asc(getattr(Order, order_column)))

        if(limit):
            query = query.limit(limit)


        # Execute the query and retrieve the results
        orders = query.all()
        if orders is None:
            return jsonify({"error": "Order not found"}), 404

        if len(orders) < 1:
            return [], 200
            
        
        serialized_data = serialize(orders)
        for index, order in enumerate(orders):
            serialized_orders = serialize(order.orders)
            serialized_user = serialize(order.user)
            serialized_data[index]["orders"] = serialized_orders
            serialized_data[index]["user"] = serialized_user
            serialized_data[index]["order_status"] = order.order_status.name
            
            for product_index, product in enumerate(order.orders):
                serialized_product = serialize(product.product)
                serialized_data[index]["orders"][product_index]['name'] = serialized_product['name']
                serialized_data[index]["orders"][product_index]['image_url'] = serialized_product['image_url']
            

        return jsonify(serialized_data), 200
    except Exception as e:
        print(e)
        return jsonify(str(e)), 500
    

def get_user_orders():
    try:
        user_id = session.get('user_id')
        # Retrieve query parameters from the request URL
        order_id = request.args.get('order_id', None)
        order_in = request.args.get('order_in', 'desc')
        order_column = request.args.get('order_column', 'created_at')
        search = request.args.get('search', None)
        limit = request.args.get('limit', None)
        
        # Create the base query for the Order table
        query = Order.query.filter_by(user_id=user_id)
        
        # Filter by 'order_id' if provided
        if order_id is not None:
            query = query.filter_by(order_id=order_id)


        # Apply search filter if 'search_term' is provided
        if search is not None:
            if search == '':
                return jsonify([]), 200
            
            # Use 'ilike' to perform a case-insensitive search on the 'name' column
            query = query.filter(Order.order_id.ilike(f"%{search}%"))


        # Determine the sorting order based on 'order'
        if order_in == 'desc':
            query = query.order_by(desc(getattr(Order, order_column)))
        else:
            query = query.order_by(asc(getattr(Order, order_column)))

        if(limit):
            query = query.limit(limit)


        # Execute the query and retrieve the results
        orders = query.all()
        if orders is None:
            return jsonify({"error": "Order not found"}), 404

        if len(orders) < 1:
            return [], 200
            
        

        serialized_data = serialize(orders)
        for index, order in enumerate(orders):
            serialized_orders = serialize(order.orders)
            serialized_data[index]["orders"] = serialized_orders
            serialized_data[index]["order_status"] = order.order_status.name
            
            for product_index, product in enumerate(order.orders):
                serialized_product = serialize(product.product)
                serialized_data[index]["orders"][product_index]['name'] = serialized_product['name']
                serialized_data[index]["orders"][product_index]['image_url'] = serialized_product['image_url']
            

        return jsonify(serialized_data), 200
    except Exception as e:
        print(e)
        return jsonify(str(e)), 500



def update_order(order_id):
    try:
        data = request.get_json()
        order_status_id = data.get('order_status_id')

        if not isinstance(order_status_id, int):
            raise ValueError("order_status_id must be an integer")

        order = Order.query.get(order_id)

        if order is None:
            raise NotFoundError({'error': "Not found", "message": f"order id:{order_id} not found."})


        if order.order_status_id >= 3:
            serialized_data = serialize(order)
            return jsonify(serialized_data), 200
        
        prev_status_id = order.order_status_id 
        order.order_status_id = order_status_id

        db.session.commit()

        # send order status email to client
        send_email(email_receiver=order.user.email, subject=f"Order has been {order.order_status.name}", body=f"Order {order.order_id} has been {order.order_status.name}, thank you for shopping with us")

        if prev_status_id != 3 and  order_status_id == 3:
            body = ""
            user_id = order.user.user_id
            for product in order.orders:     
                token = generate_token(user_id=user_id, minutes=(24 * 7) * 60)
                body += f"Leave a comment {base_url}/comment/{token.token}/{product.product_id} <br>"
            send_email(email_receiver=order.user.email, subject="Review Products", body=body)

        

        serialized_data = serialize(order)
        return jsonify(serialized_data), 200
    except (sqlalchemy.exc.SQLAlchemyError, pymysql.err.OperationalError,pymysql.err.IntegrityError) as e:
        db.session.rollback()
        print(e)
        error = {"error": "Database error"}

        if "Cannot add or update a child row: a foreign key constraint fails" in str(e):
            error['message'] = "order status doesn't exist"
        status = 400
        return jsonify(str(e)), status
    except ValueError as e:
        db.session.rollback()
        print(e)
        error = {"error": str(e)}
        status = 400
        return jsonify(str(error)), status
    except NotFoundError as e:
        db.session.rollback()
        error = e.error_dict
        status = 404
        return jsonify(str(e)), status
    except Exception as e:
        db.session.rollback()
        print(e)
        error = {'error': "Internal Error", 'message':""}
        status = 500
        return jsonify(e), status