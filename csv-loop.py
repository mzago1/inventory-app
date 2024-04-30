import boto3
import csv
from io import StringIO

# Configurações do cliente DynamoDB
dynamodb = boto3.resource('dynamodb', region_name='eu-central-1')
table = dynamodb.Table('Inventory')

# Dicionário para armazenar o último nível de estoque de cada item em cada armazém
last_stock_levels = {}

# Função para inserir itens no DynamoDB a partir de um arquivo CSV
def insert_items_from_csv(csv_body):
    csv_data = csv.DictReader(csv_body, delimiter=';')
    for row in csv_data:
        try:
            timestamp = row['Timestamp']
            warehouse_name = row['WarehouseName']
            item_id = row['ItemId']
            item_name = row['ItemName']
            stock_level_change = int(row['StockLevelChange'])

            # Verifica se o item já existe no dicionário de estoque por armazém
            if item_id in last_stock_levels:
                warehouse_stock_levels = last_stock_levels[item_id]
            else:
                warehouse_stock_levels = {}

            # Obtém o último nível de estoque do item no armazém correspondente
            if warehouse_name in warehouse_stock_levels:
                last_stock_level = warehouse_stock_levels[warehouse_name]
            else:
                last_stock_level = 0

            # Calcula a variação do estoque
            stock_level_change = stock_level_change + last_stock_level

            # Atualiza o último nível de estoque do item no armazém
            warehouse_stock_levels[warehouse_name] = int(row['StockLevelChange'])
            last_stock_levels[item_id] = warehouse_stock_levels

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

# Configurações do cliente S3
s3_client = boto3.client('s3')

# Nome do seu bucket S3
bucket_name = "unique-name-for-inventory-bucket-example"

# Prefixo do diretório no seu bucket S3
prefix = "inventory_files/"

# Listar objetos no bucket S3
response = s3_client.list_objects_v2(Bucket=bucket_name, Prefix=prefix)

# Iterar sobre os objetos encontrados
for obj in response.get('Contents', []):
    # Obter o nome do objeto (chave)
    object_key = obj['Key']
    
    # Obter o objeto do S3
    response = s3_client.get_object(Bucket=bucket_name, Key=object_key)
    
    # Ler o corpo do arquivo CSV
    csv_body = response['Body'].read().decode('utf-8')
    
    # Processar o arquivo CSV e inserir os itens no DynamoDB
    insert_items_from_csv(StringIO(csv_body))

print("Inserção de itens de todos os arquivos CSV concluída.")
