import boto3

# Initialize the DynamoDB client
client = boto3.resource('dynamodb')
table = client.Table('Inventory')

# List of warehouse options
WAREHOUSES = ["BERLIN I", "FRANKFURT I", "HANNOVER I", "HANNOVER II", "HAMBURG I", "DUISBURG I", "all"]

# Function to get a list of all items in a warehouse with inventory greater than y
def get_items_with_inventory_greater_than(warehouse_name, threshold):
    # Initialize an empty list to store the items
    items_greater_than_threshold = []

    # Retrieve items from the table for the specified warehouse
    if warehouse_name == 'all':
        response = table.scan()
    else:
        response = table.scan(FilterExpression=boto3.dynamodb.conditions.Attr('WarehouseName').eq(warehouse_name))

    # Iterate over the items and check if inventory is greater than y
    for item in response['Items']:
        stock_level_change = int(item.get('StockLevelChange', 0))
        if stock_level_change > threshold:
            item_id = item['ItemId']
            item_name = item['ItemName']
            items_greater_than_threshold.append((item_id, item_name, stock_level_change))

    return items_greater_than_threshold

# Prompt the user to select a warehouse
print("Enter the name of the warehouse", WAREHOUSES)
warehouse_name = input("Enter the name of the warehouse: ")

# Get threshold value from the user
threshold = int(input("Enter the threshold value: "))

# Get items with inventory greater than the specified threshold for the specified warehouse
items_greater_than_threshold = get_items_with_inventory_greater_than(warehouse_name, threshold)

# Print the results separated by warehouse
if warehouse_name == 'all':
    for warehouse in WAREHOUSES[:-1]:  # Exclude the 'all' option
        items_for_warehouse = get_items_with_inventory_greater_than(warehouse, threshold)
        if items_for_warehouse:
            print(f"Items in {warehouse} with inventory greater than {threshold}:")
            for item_id, item_name, stock_level_change in items_for_warehouse:
                print(f"  | ItemID: {item_id} | ItemName: {item_name} | StockLevelChange: {stock_level_change} | ")
            print()
else:
    print(f"Items in {warehouse_name} with inventory greater than {threshold}:")
    for item_id, item_name, stock_level_change in items_greater_than_threshold:
        print(f"  | ItemID: {item_id} | ItemName: {item_name} | StockLevelChange: {stock_level_change} | ")
