import boto3
from collections import defaultdict

# Initialize the DynamoDB client
client = boto3.resource('dynamodb')
table = client.Table('Inventory')

# Define a list of all warehouses
WAREHOUSES = ["BERLIN I", "FRANKFURT I", "HANNOVER I", "HANNOVER II", "HAMBURG I", "DUISBURG I"]

# Function to get item quantities for a specific warehouse
def get_item_quantities(warehouse_name):
    # Initialize a dictionary to store the quantity of each item in the specified WarehouseName
    item_quantities = defaultdict(int)

    # Retrieve items from the table for the specified warehouse
    response = table.scan(FilterExpression=boto3.dynamodb.conditions.Attr('WarehouseName').eq(warehouse_name))

    # Iterate over the items and calculate the quantity of each item in the specified WarehouseName
    for item in response['Items']:
        item_id = item['ItemId']
        item_name = item['ItemName']
        stock_change = int(item['StockLevelChange'])
        
        # Add the value of StockLevelChange to the total for the item in the specified WarehouseName
        item_quantities[(item_id, item_name)] += stock_change

    return item_quantities

# Function to print item quantities for a specific warehouse
def print_item_quantities(item_quantities):
    for (item_id, item_name), quantity in item_quantities.items():
        print(f"  | Quantity: {quantity} | ItemName: {item_name} | ItemID: {item_id} | ")

# Get input from the user
warehouse_input = input("Enter the name of the warehouse [BERLIN I, FRANKFURT I, HANNOVER I, HANNOVER II, HAMBURG I, DUISBURG I] (or use 'all' for all warehouses): ")

# If the input is 'all', get item quantities for all warehouses
if warehouse_input.lower() == 'all':
    for warehouse_name in WAREHOUSES:
        print(f"WarehouseName: {warehouse_name}")
        item_quantities = get_item_quantities(warehouse_name)
        print_item_quantities(item_quantities)
        print()
else:
    # If the input is a specific warehouse, get item quantities for that warehouse
    if warehouse_input.upper() in WAREHOUSES:
        warehouse_name = warehouse_input.upper()
        print(f"WarehouseName: {warehouse_name}")
        item_quantities = get_item_quantities(warehouse_name)
        print_item_quantities(item_quantities)
    else:
        print("Invalid warehouse name. Please enter a valid warehouse name or 'all'.")

