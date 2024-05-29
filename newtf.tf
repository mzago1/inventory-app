provider "aws" {
  region = "eu-central-1"  # Define the desired region
}

# Creation of the S3 bucket
resource "aws_s3_bucket" "inventory_files" {
  bucket = "unique-name-for-inventory-bucket-example"  # Unique name for your S3 bucket
  force_destroy = true
}

# Create the restock_lists folder in the S3 bucket
resource "aws_s3_object" "restock_lists_folder" {
  bucket = aws_s3_bucket.inventory_files.bucket
  key    = "restock_lists/"
  source = "/dev/null"  # Fictitious source to create an empty object
  force_destroy = true
}

# Upload inventory files to the S3 bucket
resource "aws_s3_object" "inventory_files" {
  for_each = fileset(path.module, "inventory_files/**/*")  # Get the list of files in the "inventory_files" directory
  bucket   = aws_s3_bucket.inventory_files.bucket  # Reference to the ID of the created S3 bucket
  key      = each.value  # Set the object key as the local file name
  source   = each.value  # Set the source as the local file name
}

# Upload restock thresholds to the S3 bucket
resource "aws_s3_object" "restock_thresholds" {
  for_each = fileset(path.module, "restock_thresholds/**/*")  # Get the list of files in the "restock_thresholds" directory
  bucket   = aws_s3_bucket.inventory_files.bucket  # Reference to the ID of the created S3 bucket
  key      = each.value  # Set the object key as the local file name
  source   = each.value  # Set the source as the local file name
}

# Define the DynamoDB table to store the inventory
resource "aws_dynamodb_table" "inventory_table" {
  name           = "Inventory"
  billing_mode   = "PAY_PER_REQUEST"
  
  hash_key       = "ItemId"
  range_key      = "WarehouseName"  # Adding WarehouseName as the range key

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

# Define the DynamoDB table for restocking
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

# Define the IAM execution role for Lambda functions
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

# Define the Lambda function to process inventory files
resource "aws_lambda_function" "inventory_handler" {
  function_name = "inventory_handler"
  filename      = "inventory_handler.zip"
  handler       = "inventory_handler.handler"  # Update to the new handler name
  runtime       = "python3.8"
  role          = aws_iam_role.lambda_execution_role.arn

   environment {
    variables = {
      TABLE_NAME      = aws_dynamodb_table.inventory_table.name
      SNS_TOPIC_ARN   = aws_sns_topic.restock_notifications.arn
      SQS_QUEUE_URL   = aws_sqs_queue.inventory_queue.url
    }
  }
}

# Define the permission policy for Lambda functions
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
          "dynamodb:Scan",
          "s3:ListBucket"
        ],
        "Resource": [
          aws_dynamodb_table.inventory_table.arn,
          aws_dynamodb_table.restock_table.arn,
          "${aws_s3_bucket.inventory_files.arn}/*",
          "${aws_s3_bucket.inventory_files.arn}"
        ]
      },
      {
        "Effect": "Allow",
        "Action": "sns:Publish",
        "Resource": aws_sns_topic.restock_notifications.arn
      }
    ]
  })
}



# Attach the permission policy to the IAM execution role
resource "aws_iam_role_policy_attachment" "lambda_execution_attachment" {
  role       = aws_iam_role.lambda_execution_role.name
  policy_arn = aws_iam_policy.lambda_execution_policy.arn
}


# Configure the S3 event to trigger the Lambda function when a new CSV file is created
resource "aws_lambda_permission" "csv_data_bucket_permission" {
  statement_id  = "AllowExecutionFromS3"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.inventory_handler.arn
  principal     = "s3.amazonaws.com"
  
  # Define the conditions to trigger the Lambda function when a new object is created in the S3 bucket
  source_arn = aws_s3_bucket.inventory_files.arn
}

resource "aws_s3_bucket_notification" "data_bucket_notifications" {
  bucket = aws_s3_bucket.inventory_files.id

  lambda_function {
    lambda_function_arn = aws_lambda_function.inventory_handler.arn
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = "inventory_files/"
    }

  lambda_function {
    lambda_function_arn = aws_lambda_function.restock_handler.arn
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = "restock_thresholds/"  # Adjust the prefix to match the directory in your S3 bucket
  }  



  depends_on = [aws_s3_bucket.inventory_files, aws_lambda_function.json_loop_handler]
}


# Define the Lambda function to process restock thresholds files
resource "aws_lambda_function" "restock_handler" {
  function_name = "restock_handler"
  filename      = "restock_handler.zip"
  handler       = "restock_handler.lambda_handler"
  runtime       = "python3.8"
  role          = aws_iam_role.lambda_execution_role.arn

  environment {
    variables = {
      TABLE_NAME = aws_dynamodb_table.inventory_table.name
      SNS_TOPIC_ARN = aws_sns_topic.restock_notifications.arn
    }
  }
}

# Configure the S3 event to trigger the Lambda function when a new restock threshold file is created
resource "aws_lambda_permission" "restock_bucket_permission" {
  statement_id  = "AllowExecutionFromS3"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.restock_handler.arn
  principal     = "s3.amazonaws.com"
  
  # Define the conditions to trigger the Lambda function when a new object is created in the S3 bucket
  source_arn = aws_s3_bucket.inventory_files.arn
}

# Define the Lambda function for processing CSV files with loop
resource "aws_lambda_function" "csv_loop_handler" {
  function_name = "csv-loop"
  filename      = "csv-loop.zip"
  handler       = "csv-loop.insert_items_from_csv"  # Make sure this handler matches your actual function handler
  runtime       = "python3.8"
  role          = aws_iam_role.lambda_execution_role.arn

  environment {
    variables = {
      TABLE_NAME = aws_dynamodb_table.inventory_table.name
    }
  }

  # Add permissions to access the S3 bucket
  depends_on = [aws_iam_policy.lambda_execution_policy]
}

# Define the Lambda function to process JSON files with loop
resource "aws_lambda_function" "json_loop_handler" {
  function_name = "json-loop"
  filename      = "json-loop.zip"
  handler       = "json-loop.process_json_files"  # Check the handler name
  runtime       = "python3.8"
  role          = aws_iam_role.lambda_execution_role.arn

  environment {
    variables = {
      TABLE_NAME = aws_dynamodb_table.restock_table.name  # Updated for the Restock table
    }
  }

  # Add permissions to access the S3 bucket
  depends_on = [aws_iam_policy.lambda_execution_policy]
}

# Configure the S3 event to trigger the Lambda function when a new JSON file is created
resource "aws_lambda_permission" "json_data_bucket_permission" {
  statement_id  = "AllowExecutionFromS3"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.json_loop_handler.arn
  principal     = "s3.amazonaws.com"
  
  # Define the conditions to trigger the Lambda function when a new object is created in the S3 bucket
  source_arn = aws_s3_bucket.inventory_files.arn
}


# Creation of the SNS topic
resource "aws_sns_topic" "restock_notifications" {
  name = "restock_notifications_topic"
}

# Subscription of the topic for your email
resource "aws_sns_topic_subscription" "email_subscription" {
  topic_arn = aws_sns_topic.restock_notifications.arn
  protocol  = "email"
  endpoint  = "mjzagobooks@gmail.com"
}

# Creation of the IAM role for Lambda related to SNS
resource "aws_iam_role" "lambda_execution_role_sns" {
  name               = "lambda_execution_role_sns"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect    = "Allow"
          "Action": [
          "dynamodb:PutItem",
          "dynamodb:GetItem",
          "dynamodb:UpdateItem",
          "s3:GetObject",
          "dynamodb:Scan",
          "s3:ListBucket"  // Add permission to list the bucket
        ],
        Principal = {
          Service = "lambda.amazonaws.com"
        }
        Action    = "sts:AssumeRole"
      }
    ]
  })
}

# Attach a policy allowing the Lambda function to access SNS
resource "aws_iam_policy_attachment" "lambda_sns_policy_attachment" {
  name       = "lambda_sns_policy_attachment"
  roles      = [aws_iam_role.lambda_execution_role_sns.name]
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_policy_attachment" "lambda_sns_policy_attachment_full" {
  name       = "lambda_sns_policy_attachment_full"
  roles      = [aws_iam_role.lambda_execution_role_sns.name]
  policy_arn = "arn:aws:iam::aws:policy/AmazonSNSFullAccess"
}

# Creation of the SNS topic policy to allow Lambda to publish messages
resource "aws_sns_topic_policy" "sns_topic_policy" {
  arn    = aws_sns_topic.restock_notifications.arn
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect    = "Allow",
        Principal = "*",
        Action    = "sns:Publish",
        Resource  = aws_sns_topic.restock_notifications.arn,
        Sid       = "AllowLambdaToPublish"
      }
    ]
  })
}

# Define the Lambda function to check inventory and send notifications
resource "aws_lambda_function" "restock_checker" {
  filename      = "restock_checker.zip"
  function_name = "restock_checker"
  role          = aws_iam_role.lambda_execution_role_sns.arn
  handler       = "restock_checker.restock_checker"
  runtime       = "python3.8"
  timeout       = 10
  memory_size   = 128

  environment {
    variables = {
      SNS_TOPIC_ARN = aws_sns_topic.restock_notifications.arn  # Pass the SNS topic ARN as an environment variable
    }
  }

  depends_on = [
    aws_iam_policy_attachment.lambda_sns_policy_attachment,
    aws_iam_policy_attachment.lambda_sns_policy_attachment_full,
  ]
}

# Adiciona a política de permissão para permitir o acesso à tabela DynamoDB 'Restock'
resource "aws_iam_policy" "dynamodb_scan_policy_restock" {
  name        = "DynamoDBScanPolicyRestock"
  description = "Policy to allow DynamoDB scan operation on the Restock table"

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect   = "Allow",
        Action   = "dynamodb:Scan",
        Resource = aws_dynamodb_table.restock_table.arn
      }
    ]
  })
}

##################################
# Define IAM policy for DynamoDB BatchWriteItem operation on Restock table
resource "aws_iam_policy" "dynamodb_batch_write_policy_restock" {
  name        = "DynamoDBBatchWritePolicyRestock"
  description = "Policy to allow DynamoDB BatchWriteItem operation on the Restock table"

  policy = jsonencode({
    Version   = "2012-10-17",
    Statement = [{
      Effect   = "Allow",
      Action   = "dynamodb:BatchWriteItem",
      Resource = aws_dynamodb_table.restock_table.arn
    }]
  })
}

# Attach the IAM policy to the appropriate role
resource "aws_iam_role_policy_attachment" "attach_dynamodb_batch_write_policy_restock" {
  role       = aws_iam_role.lambda_execution_role.name  # Replace with the name of the role you want to attach the policy to
  policy_arn = aws_iam_policy.dynamodb_batch_write_policy_restock.arn
}

##################################

# Anexa a política de permissão ao papel de execução IAM da função Lambda
resource "aws_iam_policy_attachment" "lambda_dynamodb_scan_attachment_restock" {
  name       = "LambdaDynamoDBScanAttachmentRestock"
  roles      = [aws_iam_role.lambda_execution_role.name]
  policy_arn = aws_iam_policy.dynamodb_scan_policy_restock.arn
}

# Adiciona a política de permissão para permitir o acesso à tabela DynamoDB 'Restock'
resource "aws_iam_policy" "dynamodb_read_policy_restock" {
  name        = "DynamoDBReadPolicyRestock"
  description = "Policy to allow DynamoDB read operation on the Restock table"

  policy = jsonencode({
    Version = "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Action": [
          "dynamodb:PutItem",
          "dynamodb:GetItem",
          "dynamodb:UpdateItem",
          "s3:GetObject",
          "dynamodb:Scan",
          "s3:ListBucket"  // Add permission to list the bucket
        ],
        Action   = "dynamodb:GetItem",
        Resource = aws_dynamodb_table.restock_table.arn
      }
    ]
  })
}

# Anexa a política de permissão ao papel de execução IAM da função Lambda
resource "aws_iam_policy_attachment" "lambda_dynamodb_read_attachment_restock" {
  name       = "LambdaDynamoDBReadAttachmentRestock"
  roles      = [aws_iam_role.lambda_execution_role_sns.name]
  policy_arn = aws_iam_policy.dynamodb_read_policy_restock.arn
}

# Adiciona a política de permissão para permitir o acesso à tabela DynamoDB 'Inventory'
resource "aws_iam_policy" "dynamodb_read_policy_inventory" {
  name        = "DynamoDBReadPolicyInventory"
  description = "Policy to allow DynamoDB read operation on the Inventory table"

  policy = jsonencode({
    Version = "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Action": [
          "dynamodb:PutItem",
          "dynamodb:GetItem",
          "dynamodb:UpdateItem",
          "s3:GetObject",
          "dynamodb:Scan",
          "s3:ListBucket"  // Add permission to list the bucket
        ],
        Resource = aws_dynamodb_table.inventory_table.arn
      }
    ]
  })
}

# Anexa a política de permissão ao papel de execução IAM da função Lambda
resource "aws_iam_policy_attachment" "lambda_dynamodb_read_attachment_inventory" {
  name       = "LambdaDynamoDBReadAttachmentInventory"
  roles      = [aws_iam_role.lambda_execution_role_sns.name]
  policy_arn = aws_iam_policy.dynamodb_read_policy_inventory.arn
}

# Adiciona a política de permissão para permitir o acesso à tabela DynamoDB 'Inventory'
resource "aws_iam_policy" "dynamodb_scan_policy_inventory" {
  name        = "DynamoDBScanPolicyInventory"
  description = "Policy to allow DynamoDB scan operation on the Inventory table"

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect   = "Allow",
        Action   = "dynamodb:Scan",
        Resource = aws_dynamodb_table.inventory_table.arn
      }
    ]
  })
}

# Anexa a política de permissão ao papel de execução IAM da função Lambda
resource "aws_iam_policy_attachment" "lambda_dynamodb_scan_attachment_inventory" {
  name       = "LambdaDynamoDBScanAttachmentInventory"
  roles      = [aws_iam_role.lambda_execution_role_sns.name]
  policy_arn = aws_iam_policy.dynamodb_scan_policy_inventory.arn
}

###############
resource "aws_iam_policy" "lambda_sns_policy_publish" {
  name        = "LambdaSNSPolicyPublish"
  description = "Policy to allow Lambda to publish messages to SNS"

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect    = "Allow",
        Action    = "sns:Publish",
        Resource  = aws_sns_topic.restock_notifications.arn
      }
    ]
  })
}

# Anexa a política de permissão ao papel de execução IAM da função Lambda
resource "aws_iam_policy_attachment" "lambda_sns_policy_attachment_publish" {
  name       = "LambdaSNSSendAttachment"
  roles      = [aws_iam_role.lambda_execution_role_sns.name]
  policy_arn = aws_iam_policy.lambda_sns_policy_publish.arn
}
##########################
##########################

# Criação da fila SQS
resource "aws_sqs_queue" "inventory_queue" {
  name = "inventory_queue"
}

# Política IAM para envio de mensagens para a fila SQS
resource "aws_iam_policy" "sqs_send_message_policy" {
  name        = "SQSSendMessagePolicy"
  description = "Policy to allow sending messages to SQS queues"

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Effect    = "Allow",
      Action    = [
        "sqs:SendMessage",
      ],
      Resource  = aws_sqs_queue.inventory_queue.arn,
    }],
  })
}

resource "aws_iam_role_policy_attachment" "lambda_sqs_send_message_attachment" {
  role       = aws_iam_role.lambda_execution_role.name
  policy_arn = aws_iam_policy.sqs_send_message_policy.arn
}


resource "aws_sqs_queue_policy" "inventory_queue_policy" {
  queue_url = aws_sqs_queue.inventory_queue.id

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Principal = "*",
        Action = "sqs:SendMessage",
        Resource = aws_sqs_queue.inventory_queue.arn,
        Condition = {
          ArnLike = {
            "aws:SourceArn": aws_s3_bucket.inventory_files.arn
          }
        }
      }
    ]
  })
}
############################



# Create the IAM role for Step Functions
resource "aws_iam_role" "step_function_role" {
  name = "StepFunctionExecutionRole"

  assume_role_policy = jsonencode({
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Principal": {
          "Service": "states.eu-central-1.amazonaws.com"
        },
        "Action": "sts:AssumeRole"
      }
    ]
  })
}

# Attach policies to the Step Function role
resource "aws_iam_role_policy" "step_function_policy" {
  name = "StepFunctionPolicy"
  role = aws_iam_role.step_function_role.id

  policy = jsonencode({
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Action": [
          "lambda:InvokeFunction",
          "lambda:InvokeAsync"
        ],
        "Resource": [
          aws_lambda_function.sqs_consumer_lambda.arn
        ]
      },
      {
        "Effect": "Allow",
        "Action": "sqs:ReceiveMessage",
        "Resource": aws_sqs_queue.inventory_queue.arn
      }
    ]
  })
}

# Define the Lambda function to process SQS messages
# Define the Lambda function to process SQS messages
resource "aws_lambda_function" "sqs_consumer_lambda" {
  function_name = "sqs-consumer-lambda"
  filename      = "batch_operation.zip"
  handler       = "batch_operation.lambda_handler"
  runtime       = "python3.8"
  role          = aws_iam_role.lambda_execution_role.arn

  timeout       = 900  # Max allowed timeout is 15 minutes

  environment {
    variables = {
      SQS_QUEUE_URL = aws_sqs_queue.inventory_queue.url,
      SNS_TOPIC_ARN = aws_sns_topic.restock_notifications.arn # Replace `your_topic` with your SNS topic name
    }
  }
}

# Step Function definition
data "aws_iam_policy_document" "step_function_policy" {
  statement {
    actions   = ["lambda:InvokeFunction"]
    resources = [aws_lambda_function.sqs_consumer_lambda.arn]
    effect    = "Allow"
  }
}

resource "aws_sfn_state_machine" "sqs_processor" {
  name     = "SQSProcessor"
  role_arn = aws_iam_role.step_function_role.arn
  definition = jsonencode({
    "Comment": "A description of my state machine",
    "StartAt": "ProcessSQSMessage",
    "States": {
      "ProcessSQSMessage": {
        "Type": "Task",
        "Resource": aws_lambda_function.sqs_consumer_lambda.arn,
        "Next": "WaitState",
        "Retry": [
          {
            "ErrorEquals": ["States.ALL"],
            "IntervalSeconds": 5,
            "MaxAttempts": 3,
            "BackoffRate": 2
          }
        ],
        "Catch": [
          {
            "ErrorEquals": ["States.ALL"],
            "Next": "FailState"
          }
        ]
      },
      "WaitState": {
        "Type": "Wait",
        "Seconds": 10,
        "Next": "ProcessSQSMessage"
      },
      "FailState": {
        "Type": "Fail",
        "Error": "Failed to process SQS messages"
      }
    }
  })
}

# Schedule to run Step Function daily at 3 AM UTC
resource "aws_cloudwatch_event_rule" "daily_sqs_processor_trigger" {
  name                = "DailySQSProcessorTrigger"
  schedule_expression = "cron(0 3 * * ? *)"
}

resource "aws_cloudwatch_event_target" "sqs_processor_target" {
  rule      = aws_cloudwatch_event_rule.daily_sqs_processor_trigger.name
  target_id = "SQSProcessorStepFunction"
  arn       = aws_sfn_state_machine.sqs_processor.arn
  role_arn  = aws_iam_role.step_function_role.arn  # Added role_arn here
}

resource "aws_lambda_permission" "allow_cloudwatch_to_invoke_lambda" {
  statement_id  = "AllowCloudWatch"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.sqs_consumer_lambda.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.daily_sqs_processor_trigger.arn
}

# Attach policy to allow Step Function to be triggered by CloudWatch
resource "aws_iam_role_policy" "step_function_cloudwatch_policy" {
  name = "StepFunctionCloudWatchPolicy"
  role = aws_iam_role.step_function_role.id
  policy = jsonencode({
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Action": "states:StartExecution",
        "Resource": aws_sfn_state_machine.sqs_processor.arn
      }
    ]
  })
}

resource "aws_iam_policy" "sqs_receive_message_policy" {
  name        = "SQSReceiveMessagePolicy"
  description = "Policy to allow receiving messages from SQS queue"

  policy = jsonencode({
    Version   = "2012-10-17",
    Statement = [{
      Effect   = "Allow",
      "Action": ["sqs:ReceiveMessage",
                 "sqs:DeleteMessage"],
      Resource = aws_sqs_queue.inventory_queue.arn,
    }],
  })
}

resource "aws_iam_role_policy_attachment" "lambda_sqs_receive_message_attachment" {
  role       = aws_iam_role.lambda_execution_role.name
  policy_arn = aws_iam_policy.sqs_receive_message_policy.arn
}



