import boto3

# Initialize DynamoDB client
client = boto3.client('dynamodb')

# Function to query DynamoDB and get the item name and quantity in a specific warehouse
def get_item_quantity(item_id, warehouse_name):
    response = client.query(
        TableName='Inventory',
        KeyConditionExpression='#i = :item_id AND #w = :warehouse_name',
        ExpressionAttributeNames={
            '#i': 'ItemId',
            '#w': 'WarehouseName'
        },
        ExpressionAttributeValues={
            ':item_id': {'S': item_id},
            ':warehouse_name': {'S': warehouse_name}
        }
    )
    if 'Items' in response and len(response['Items']) > 0:
        item = response['Items'][0]
        item_name = item['ItemName']['S']
        stock_level_change = int(item['StockLevelChange']['N'])
        return item_name, stock_level_change
    else:
        return None, 0  # Return 0 if no corresponding item found

# Ask user for ItemId and WarehouseName
item_id = input("Enter the ItemId: ")
warehouse_name = input("Enter the WarehouseName [BERLIN I, FRANKFURT I, HANNOVER I, HANNOVER II, HAMBURG I, DUISBURG I] (or type 'all' to get quantities for all warehouses): ").upper()

if warehouse_name == 'ALL':
    warehouses = ['BERLIN I', 'FRANKFURT I', 'HANNOVER I', 'HANNOVER II', 'HAMBURG I', 'DUISBURG I']
else:
    warehouses = [warehouse_name]

# Loop through each warehouse and get the item quantity
for warehouse in warehouses:
    item_name, quantity = get_item_quantity(item_id, warehouse)

    # Display the result for each warehouse
    if item_name is not None:
        print(f"In '{warehouse}', item '{item_id}' - '{item_name}' has {quantity} units.")
    else:
        print(f"No information for your item in '{warehouse}'.")
