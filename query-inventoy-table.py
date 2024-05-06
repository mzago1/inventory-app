import boto3
from collections import defaultdict

# Initialize the DynamoDB client
client = boto3.resource('dynamodb')
table = client.Table('Inventory')

# Initialize a dictionary to store the quantity of each item in each WarehouseName
item_quantities = defaultdict(lambda: defaultdict(int))

# Retrieve all items from the table
response = table.scan()

# Iterate over the items and calculate the quantity of each item in each WarehouseName
for item in response['Items']:
    warehouse_name = item['WarehouseName']
    item_id = item['ItemId']
    item_name = item['ItemName']
    stock_change = int(item['StockLevelChange'])
    
    # Add the value of StockLevelChange to the total for the item in the corresponding WarehouseName
    item_quantities[warehouse_name][(item_id, item_name)] += stock_change

# Print the results
for warehouse_name, items in item_quantities.items():
    print(f"WarehouseName: {warehouse_name}")
    for (item_id, item_name), quantity in items.items():
        print(f"  | Quantity: {quantity} | ItemName: {item_name} | ItemID: {item_id} | ")
    print()
