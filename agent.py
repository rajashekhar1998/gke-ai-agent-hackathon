import sys
import os
import grpc
import google.generativeai as genai

# Add the 'pb' directory to Python's import path
sys.path.insert(0, os.path.abspath('./pb'))

# Now we can import the generated gRPC modules directly
import demo_pb2
import demo_pb2_grpc

from google.protobuf.json_format import MessageToJson
import json


def get_all_products():
    """
    Connects to the ProductCatalogService and fetches all products.
    """
    print("--- Connecting to Product Catalog Service... ---")
    # Establish a connection to the gRPC server
    channel = grpc.insecure_channel('localhost:3550')

    # Create a client "stub" to call the service's methods
    stub = demo_pb2_grpc.ProductCatalogServiceStub(channel)

    # Call the ListProducts method using an Empty request message
    request = demo_pb2.Empty()
    response = stub.ListProducts(request)

    print("--- Successfully fetched products ---")
    return response.products  # <-- Add this line


def get_ai_recommendations(user_query, products):
    """
    Sends the user's query and product list to the Gemini API for recommendations.
    """
    # Configure the Gemini API key from environment variables
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY environment variable not set.")
    genai.configure(api_key=api_key)

    model = genai.GenerativeModel('gemini-1.5-flash')

    # Convert the list of protobuf objects to a clean JSON string
    products_json_list = [MessageToJson(p) for p in products]
    products_json = json.dumps(products_json_list)

    # Create a detailed prompt for the AI
    prompt = f"""
    You are an expert personal shopper for an online boutique.
    A customer has the following request: "{user_query}"

    Here is the list of available products in the store, in JSON format:
    {products_json}

    Please analyze the customer's request and the product data. Recommend a set of products from the list.
    Your response should be ONLY a comma-separated list of the product IDs for your recommendations.
    For example: "1YMWWN1N4O,L9ECAV7KIM,OLJCESPC7Z"
    """

    print("\n--- Sending prompt to Gemini AI... ---")
    response = model.generate_content(prompt)
    print("--- Received response from AI ---")

    return response.text


if __name__ == '__main__':
    # 1. Get a shopping request from the user
    user_request = input("Welcome to the AI Personal Shopper! What are you looking for today?\n> ")

    # 2. Fetch all available products from the microservice
    product_list = get_all_products()

    # 3. Ask the AI for recommendations
    if product_list:
        recommendations_str = get_ai_recommendations(user_request, product_list)

        # 4. Process and display the recommended products
        recommended_ids = [rid.strip() for rid in recommendations_str.split(',')]

        print("\n--- Here are your AI-powered recommendations! ---")
        found_products = False
        for product in product_list:
            if product.id in recommended_ids:
                # Format the price nicely from units and nanos
                price = f"{product.price_usd.units}.{str(product.price_usd.nanos // 10000000).zfill(2)}"
                print(f"\n- {product.name} (${price})")
                print(f"  ID: {product.id}")
                print(f"  '{product.description}'")
                found_products = True

        if not found_products:
            print("The AI didn't recommend any products currently in the catalog.")
    else:
        print("Could not retrieve product list.")
