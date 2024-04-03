import boto3

# Initialize a DynamoDB resource using boto3
dynamodb = boto3.resource('dynamodb')

# Create the DynamoDB table.
try:
    table = dynamodb.create_table(
        TableName='music',
        KeySchema=[
            {
                'AttributeName': 'title',
                'KeyType': 'HASH'  # Partition key
            },
            {
                'AttributeName': 'artist',
                'KeyType': 'RANGE'  # Sort key
            }
        ],
        AttributeDefinitions=[
            {
                'AttributeName': 'title',
                'AttributeType': 'S'
            },
            {
                'AttributeName': 'artist',
                'AttributeType': 'S'
            },
            # Even though 'year', 'web_url', and 'image_url' are attributes,
            # they do not need to be defined here since they're not key schema attributes.
        ],
        ProvisionedThroughput={
            'ReadCapacityUnits': 1,
            'WriteCapacityUnits': 1
        }
    )
    # Wait for the table to be created
    table.meta.client.get_waiter('table_exists').wait(TableName='music')
    print(f"Table {table.table_name} created successfully!")
except boto3.exceptions.botocore.client.ClientError as e:
    # If the table already exists, catch the exception and print a message
    if e.response['Error']['Code'] == 'ResourceInUseException':
        print("Table already exists. Continue with the next operations.")
    else:
        raise
