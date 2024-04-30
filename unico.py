import boto3
from datetime import datetime

# Configurações do cliente DynamoDB
dynamodb = boto3.resource('dynamodb', region_name='eu-central-1')
table = dynamodb.Table('Inventory')

# Esta função é acionada quando a Lambda é invocada
def unico(event, context):
    try:
        # Criar um item fictício para inserir no DynamoDB
        timestamp = datetime.now().isoformat()
        warehouse_name = "WarehouseA"
        item_id = "123456"
        item_name = "ItemXYZ"
        stock_level_change = 10

        # Objeto de item para inserção no DynamoDB
        item = {
            'Timestamp': timestamp,
            'WarehouseName': warehouse_name,
            'ItemId': item_id,
            'ItemName': item_name,
            'StockLevelChange': stock_level_change
        }

        # Inserir o item no DynamoDB
        table.put_item(Item=item)

        print(f"Inserido com sucesso: {item}")
    except Exception as e:
        print(f"Falha ao inserir: {str(e)}")
