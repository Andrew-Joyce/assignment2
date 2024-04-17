from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, current_app
import boto3
from botocore.exceptions import ClientError

app = Flask(__name__)
app.secret_key = 'andrew_joyce'

dynamodb = boto3.client('dynamodb', region_name='ap-southeast-2')

def check_credentials(email, password):
    print(f"Checking credentials for email: '{email}', password: '{password}'")
    try:
        response = dynamodb.get_item(
            TableName='login',
            Key={
                'email': {'S': email.strip()}
            }
        )
        print(f"DynamoDB response: {response}")
        if 'Item' in response:
            stored_password = response['Item'].get('password', {}).get('S')
            if stored_password == password:
                return True, email
            else:
                print("Incorrect password retrieved from DynamoDB:", stored_password)
                return False, None
        else:
            print("No item found in DynamoDB for email:", email)
            return False, None
    except ClientError as e:
        error_message = f"Error accessing DynamoDB table: {e.response['Error']['Message']}"
        print(error_message)
        print(e.response)
        return False, None

@app.route("/", methods=["GET"])
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        authenticated, _ = check_credentials(email, password)
        if authenticated:
            # Store user email in session upon successful login
            session['email'] = email
            return redirect(url_for('main_page', email=email))
        else:
            error = 'Email or password is invalid'

    return render_template('login.html', error=error)

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form['email']
        username = request.form['username']
        password = request.form['password']

        try:
            response = dynamodb.get_item(
                TableName='login',
                Key={
                    'email': {'S': email}
                }
            )
            if 'Item' in response:
                flash('Email already registered. Please log in or use a different email.')
                return redirect(url_for('register'))
            else:
                dynamodb.put_item(
                    TableName='login',
                    Item={
                        'email': {'S': email},
                        'username': {'S': username},
                        'password': {'S': password}  
                    }
                )
                flash('Registration successful. Please log in.')
                return redirect(url_for('login'))
        except ClientError as e:
            flash(f"Error accessing DynamoDB: {e.response['Error']['Message']}")
            return redirect(url_for('register'))

    return render_template('register.html')

def get_username(email):
    try:
        response = dynamodb.get_item(
            TableName='login',
            Key={
                'email': {'S': email.strip()}
            }
        )
        if 'Item' in response:
            return response['Item'].get('username', {}).get('S')
        else:
            return None
    except ClientError as e:
        flash(f"Error fetching username: {e.response['Error']['Message']}")
        return None


def get_subscriptions(user_email):
    try:
        response = dynamodb.scan(
            TableName='music',
            FilterExpression='user_email = :email',
            ExpressionAttributeValues={':email': {'S': user_email}}
        )
        return response.get('Items', [])
    except ClientError as e:
        flash(f"Error fetching subscriptions: {e.response['Error']['Message']}")
        return []

def get_artist_image(artist):
    return None

@app.route("/main_page", methods=["GET"])
def main_page():
    email = request.args.get('email')
    if not email:
        flash('You must be logged in to access the main page.')
        return redirect(url_for('login'))

    username = get_username(email)
    if not username:
        flash('Username not found.')
        return redirect(url_for('login'))

    try:
        response = dynamodb.scan(TableName='music')
        music_items = []
        for item in response.get('Items', []):
            music_item = {}
            for key, value in item.items():
                if 'S' in value:
                    music_item[key] = value['S']
                elif 'N' in value:
                    music_item[key] = value['N']
                elif 'L' in value:
                    music_item[key] = ', '.join(v['S'] for v in value['L'] if 'S' in v)
                elif 'M' in value:
                    music_item[key] = str({k: v.get('S', '') for k, v in value['M'].items()})
                else:
                    music_item[key] = 'Undefined or missing type'
            music_items.append(music_item)
    except ClientError as e:
        flash(f"Error fetching music items: {e.response['Error']['Message']}")
        music_items = []

    return render_template('main_page.html', username=username, subscriptions=music_items)

@app.route("/query_music", methods=["POST"])
def query_music():
    if not request.is_json:
        return 'Content-Type not supported', 415

    data = request.get_json()
    if not data:
        return jsonify({'error': 'Missing data'}), 400

    title = data.get('title', '').strip()
    artist = data.get('artist', '').strip()
    year = data.get('year', '').strip()

    filter_expressions = []
    expression_attribute_names = {}
    expression_attributes = {}

    if title:
        filter_expressions.append("contains(#t, :title)")
        expression_attribute_names['#t'] = 'title'
        expression_attributes[':title'] = {'S': title}
    if artist:
        filter_expressions.append("contains(#a, :artist)")
        expression_attribute_names['#a'] = 'artist'
        expression_attributes[':artist'] = {'S': artist}
    if year:
        filter_expressions.append("#y = :year")
        expression_attribute_names['#y'] = 'year'
        expression_attributes[':year'] = {'S': year}

    filter_expression = " AND ".join(filter_expressions) if filter_expressions else None

    try:
        if filter_expression:
            response = dynamodb.scan(
                TableName='music',
                FilterExpression=filter_expression,
                ExpressionAttributeNames=expression_attribute_names,
                ExpressionAttributeValues=expression_attributes
            )
        else:
            return jsonify({'message': "No search criteria were provided"}), 400

        items = response.get('Items', [])
        if not items:
            return jsonify({'message': "No result is retrieved. Please query again"}), 200

        queried_music = [{
            'title': item.get('title', {}).get('S', 'No Title Provided'),
            'artist': item.get('artist', {}).get('S', 'No Artist Provided'),
            'year': item.get('year', {}).get('S', 'No Year Provided'),
            'img_url': item.get('img_url', {}).get('S', ''),
            'subscribe_id': item.get('id', {}).get('S', '')
        } for item in items]

        return jsonify(queried_music)
    except ClientError as e:
        current_app.logger.error(f"DynamoDB Client Error: {e}")
        return jsonify({'error': 'Error fetching from DynamoDB'}), 500
    except Exception as e:
        current_app.logger.error(f"Server Error: {e}")
        return jsonify({'error': 'Internal Server Error'}), 500

@app.route("/unsubscribe", methods=["POST"])
def remove_subscription():
    subscription_id = request.form.get('subscription_id')

    try:
        response = dynamodb.delete_item(
            TableName='user_subscriptions',  
            Key={
                'user_email': {'S': session.get('email')},
                'music_id': {'S': subscription_id},  
            }
        )
        return jsonify({'message': 'Unsubscription successful'}), 200

    except ClientError as e:
        return jsonify({'error': str(e.response['Error']['Message'])}), 500

if __name__ == "__main__":
    app.run(debug=True)
