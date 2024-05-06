import boto3
from collections import defaultdict

# Inicialize o cliente do DynamoDB
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('Inventory')

def get_items_by_date(date):
    try:
        # Initialize a dictionary to store the quantity of each item in each WarehouseName
        item_quantities = defaultdict(lambda: defaultdict(int))

        # Retrieve items from the table for the specified date
        response = table.scan()

        # Iterate over the items and calculate the quantity of each item in each WarehouseName
        for item in response['Items']:
            item_date = item['Timestamp'].split('T')[0]  # Pegue apenas a parte da data do timestamp
            if item_date == date:
                warehouse_name = item['WarehouseName']
                item_id = item['ItemId']
                item_name = item['ItemName']
                stock_change = int(item['StockLevelChange'])
                
                # Add the value of StockLevelChange to the total for the item in the corresponding WarehouseName
                item_quantities[warehouse_name][(item_id, item_name)] += stock_change

        # Print the results
        if item_quantities:
            for warehouse_name, items in item_quantities.items():
                print(f"WarehouseName: {warehouse_name}")
                for (item_id, item_name), quantity in items.items():
                    print(f"  | Quantity: {quantity} | ItemName: {item_name} | ItemID: {item_id} | ")
                print()
        else:
            print("Nenhum item encontrado para a data especificada.")

    except Exception as e:
        print("Ocorreu um erro ao acessar o DynamoDB:", e)

# Input da data que você deseja buscar (no formato 'xxxx-xx-xx')
date_to_search = input("Digite a data no formato 'yyyy-mm-dd' para buscar os itens: ")

# Chame a função para buscar os itens pela data especificada
get_items_by_date(date_to_search)
