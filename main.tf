provider "aws" {
  region = "eu-central-1"  # Define a região desejada
}

# Criação do bucket S3
resource "aws_s3_bucket" "inventory_files" {
  bucket = "unique-name-for-inventory-bucket-example"  # Nome único para o seu bucket S3
}

# Cria a pasta restock_lists no bucket S3
resource "aws_s3_object" "restock_lists_folder" {
  bucket = aws_s3_bucket.inventory_files.bucket
  key    = "restock_lists/"
  source = "/dev/null"  # Origem fictícia para criar um objeto vazio
}

# Upload dos arquivos de inventário para o bucket S3
resource "aws_s3_object" "inventory_files" {
  for_each = fileset(path.module, "inventory_files/**/*")  # Obtém a lista de arquivos no diretório "inventory_files"
  bucket   = aws_s3_bucket.inventory_files.bucket  # Referência ao ID do bucket S3 criado
  key      = each.value  # Define a chave do objeto como o nome do arquivo local
  source   = each.value  # Define a origem como o nome do arquivo local
}

# Upload dos limiares de reabastecimento para o bucket S3
resource "aws_s3_object" "restock_thresholds" {
  for_each = fileset(path.module, "restock_thresholds/**/*")  # Obtém a lista de arquivos no diretório "restock_thresholds"
  bucket   = aws_s3_bucket.inventory_files.bucket  # Referência ao ID do bucket S3 criado
  key      = each.value  # Define a chave do objeto como o nome do arquivo local
  source   = each.value  # Define a origem como o nome do arquivo local
}

# Define a tabela DynamoDB para armazenar o inventário
resource "aws_dynamodb_table" "inventory_table" {
  name           = "Inventory"
  billing_mode   = "PAY_PER_REQUEST"
  
  hash_key       = "ItemId"
  range_key      = "WarehouseName"  # Adicionando WarehouseName como a chave de intervalo

  attribute {
    name = "ItemId"
    type = "S"
  }
  
  attribute {
    name = "WarehouseName"
    type = "S"
  }
  
  attribute {
    name = "Timestamp"
    type = "S"
  }
  
  attribute {
    name = "ItemName"
    type = "S"
  }
  
  attribute {
    name = "StockLevelChange"
    type = "N"
  }
  
  global_secondary_index {
    name               = "StockLevelChangeIndex"
    hash_key           = "StockLevelChange"
    projection_type    = "ALL"
  }
  
  global_secondary_index {
    name               = "ItemNameIndex"
    hash_key           = "ItemName"
    projection_type    = "ALL"
  }
  
  global_secondary_index {
    name               = "WarehouseNameIndex"
    hash_key           = "WarehouseName"
    projection_type    = "ALL"
  }
  
  global_secondary_index {
    name               = "TimestampIndex"
    hash_key           = "Timestamp"
    projection_type    = "ALL"
  }
}

# Define a tabela DynamoDB para reabastecimento
resource "aws_dynamodb_table" "restock_table" {
  name           = "Restock"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "ItemId"

  attribute {
    name = "ItemId"
    type = "S"
  }

  attribute {
    name = "RestockIfBelow"
    type = "N"
  }

  tags = {
    Name = "Restock Table"
  }

  global_secondary_index {
    name               = "RestockIfBelowIndex"
    hash_key           = "RestockIfBelow"
    projection_type    = "ALL"
  }
}

# Define o papel de execução IAM para as funções Lambda
resource "aws_iam_role" "lambda_execution_role" {
  name = "lambda_execution_role"

  assume_role_policy = jsonencode({
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Principal": {
          "Service": "lambda.amazonaws.com"
        },
        "Action": "sts:AssumeRole"
      }
    ]
  })
}

# Define a política de permissão para as funções Lambda
resource "aws_iam_policy" "lambda_execution_policy" {
  name   = "lambda_execution_policy"
  policy = jsonencode({
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Action": [
          "dynamodb:PutItem",
          "dynamodb:GetItem",
          "dynamodb:UpdateItem",
          "s3:GetObject",
          "s3:ListBucket"  // Adicione permissão para listar o bucket
        ],
        "Resource": [
          aws_dynamodb_table.inventory_table.arn,
          aws_dynamodb_table.restock_table.arn,
          "${aws_s3_bucket.inventory_files.arn}/*",
          "${aws_s3_bucket.inventory_files.arn}"  // Adicione permissão para o próprio bucket
        ]
      }
    ]
  })
}

# Anexa a política de permissão ao papel de execução IAM
resource "aws_iam_role_policy_attachment" "lambda_execution_attachment" {
  role       = aws_iam_role.lambda_execution_role.name
  policy_arn = aws_iam_policy.lambda_execution_policy.arn
}

# Define a função Lambda para processar os arquivos de inventário
resource "aws_lambda_function" "inventory_handler" {
  function_name = "inventory_handler"
  filename      = "inventory_handler.zip"
  handler       = "inventory_handler.handler"  # Atualize para o novo nome do handler
  runtime       = "python3.8"
  role          = aws_iam_role.lambda_execution_role.arn

  environment {
    variables = {
      TABLE_NAME = aws_dynamodb_table.inventory_table.name
    }
  }
}

# Configura o evento S3 para acionar a função Lambda quando um novo arquivo for criado
resource "aws_lambda_permission" "inventory_bucket_permission" {
  statement_id  = "AllowExecutionFromS3"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.inventory_handler.arn
  principal     = "s3.amazonaws.com"
  
  # Define as condições para acionar a função Lambda quando um novo objeto é criado no bucket S3
  source_arn = aws_s3_bucket.inventory_files.arn
}

resource "aws_s3_bucket_notification" "inventory_bucket_notification" {
  bucket = aws_s3_bucket.inventory_files.id

  lambda_function {
    lambda_function_arn = aws_lambda_function.inventory_handler.arn
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = "inventory_files/"
  }
}

# Define a função Lambda para processar os arquivos de limiares de reabastecimento
resource "aws_lambda_function" "restock_handler" {
  function_name = "restock-handler"
  filename      = "lambda-restock.zip"
  handler       = "lambda.handler"
  runtime       = "python3.8"
  role          = aws_iam_role.lambda_execution_role.arn

  environment {
    variables = {
      TABLE_NAME = aws_dynamodb_table.inventory_table.name
    }
  }
}

# Configura o evento S3 para acionar a função Lambda quando um novo arquivo de limiares de reabastecimento é criado
resource "aws_lambda_permission" "restock_bucket_permission" {
  statement_id  = "AllowExecutionFromS3"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.restock_handler.arn
  principal     = "s3.amazonaws.com"
  
  # Define as condições para acionar a função Lambda quando um novo objeto é criado no bucket S3
  source_arn = aws_s3_bucket.inventory_files.arn
}

resource "aws_s3_bucket_notification" "restock_bucket_notification" {
  bucket = aws_s3_bucket.inventory_files.id

  lambda_function {
    lambda_function_arn = aws_lambda_function.restock_handler.arn
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = "restock_thresholds/"
  }
}

# Define a função Lambda para inserir dados no DynamoDB a partir do arquivo CSV
resource "aws_lambda_function" "csv_data_handler" {
  function_name = "csv-data"
  filename      = "csv-data.zip"
  handler       = "csv-data.insert_items_from_csv"  # Verifique se o nome do manipulador está correto
  runtime       = "python3.8"
  role          = aws_iam_role.lambda_execution_role.arn

  environment {
    variables = {
      TABLE_NAME = aws_dynamodb_table.inventory_table.name
    }
  }
}


# Configura o evento S3 para acionar a função Lambda quando um novo arquivo CSV é criado
resource "aws_lambda_permission" "csv_data_bucket_permission" {
  statement_id  = "AllowExecutionFromS3"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.csv_data_handler.arn
  principal     = "s3.amazonaws.com"
  
  # Define as condições para acionar a função Lambda quando um novo objeto é criado no bucket S3
  source_arn = aws_s3_bucket.inventory_files.arn
}

resource "aws_s3_bucket_notification" "csv_data_bucket_notification" {
  bucket = aws_s3_bucket.inventory_files.id

  lambda_function {
    lambda_function_arn = aws_lambda_function.csv_data_handler.arn
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = "csv/"
  }
}

# Define a função Lambda para processar os arquivos CSV com loop
resource "aws_lambda_function" "csv_loop_handler" {
  function_name = "csv-loop"
  filename      = "csv-loop.zip"
  handler       = "csv-loop.insert_items_from_csv"  # Verifique se o nome do manipulador está correto
  runtime       = "python3.8"
  role          = aws_iam_role.lambda_execution_role.arn

  environment {
    variables = {
      TABLE_NAME = aws_dynamodb_table.inventory_table.name
    }
  }

  # Adiciona permissões para acessar o bucket S3
  depends_on = [aws_iam_policy.lambda_execution_policy]
}
