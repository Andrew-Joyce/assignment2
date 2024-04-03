import json
import boto3

dynamodb = boto3.client('dynamodb', region_name='ap-southeast-2')

table_name = 'music'

json_file_path = '/Users/andrewjoyce/Downloads/a2.json' 
with open(json_file_path, 'r') as file:
    data = json.load(file)
    music_data = data['songs']

dynamo_items = []
for item in music_data:
    dynamo_item = {
        'title': {'S': item['title']},
        'artist': {'S': item['artist']},
        'year': {'S': item['year']},  
        'web_url': {'S': item['web_url']},
        'img_url': {'S': item['img_url']}
    }
    dynamo_items.append({'PutRequest': {'Item': dynamo_item}})

def batch_write(dynamodb, table_name, items):
    for i in range(0, len(items), 25):
        batch = items[i:i+25]
        response = dynamodb.batch_write_item(RequestItems={table_name: batch})
        if response['UnprocessedItems']:
            print('Some items could not be processed:', response['UnprocessedItems'])
        else:
            print('Batch write successful for items', i, 'to', i + len(batch))

batch_write(dynamodb, table_name, dynamo_items)

