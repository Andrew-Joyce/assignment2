import logging
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import boto3
from boto3.dynamodb.conditions import Attr
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key

app = Flask(__name__)
app.secret_key = 'andrew_joyce'

dynamodb = boto3.resource('dynamodb', region_name='ap-southeast-2')
music_table = dynamodb.Table('music')

def check_credentials(email, password):
    try:
        response = boto3.client('dynamodb').get_item(
            TableName='login',
            Key={
                'email': {'S': email.strip()}
            }
        )
        if 'Item' in response:
            username = response['Item'].get('username', {}).get('S')
            stored_password = response['Item'].get('password', {}).get('S')
            if stored_password == password:
                return True, username
            else:
                return False, None
        else:
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
    if request.method == 'POST':
        email = request.form['email']  
        password = request.form['password']  
        authenticated, username = check_credentials(email, password)  
        if authenticated:
            session['logged_in'] = True  
            session['username'] = username  # Storing username in session
            app.logger.debug(f"User logged in: {username}")  
            return redirect(url_for('main_page'))  
        else:
            flash('Email or password is invalid')  
    return render_template('login.html')


@app.route('/main_page', methods=['GET', 'POST'])
def main_page():
    results = []
    if request.method == 'POST' and 'logged_in' in session and session['logged_in']:
        title = request.form.get('title', '')
        artist = request.form.get('artist', '')
        year = request.form.get('year', '')

        condition = None
        if title:
            condition = Attr('title').contains(title)
        if artist:
            condition = (condition & Attr('artist').contains(artist)) if condition else Attr('artist').contains(artist)
        if year:
            condition = (condition & Attr('year').contains(year)) if condition else Attr('year').contains(year)

        if condition:
            try:
                response = music_table.scan(FilterExpression=condition)
                results = response['Items']
            except ClientError as e:
                logging.error(f"Error performing search: {e.response['Error']['Message']}")
                flash('Error performing search.', 'error')

    # Pass the username to the template
    username = session.get('username')
    return render_template('main_page.html', results=results, username=username)


@app.route('/subscriptions', methods=['GET'])
def fetch_subscriptions():
    if 'logged_in' in session and session['logged_in']:
        email = session.get('email')
        if not email:
            logging.error("No email found in session")
            return jsonify({'error': 'Session error'}), 400

        dynamodb = boto3.resource('dynamodb')
        music_table = dynamodb.Table('music')
        try:
            subscription_response = music_table.scan(
                FilterExpression=Attr('subscriptions').contains(email)
            )
            subscriptions = subscription_response['Items']
            return jsonify(subscriptions), 200
        except Exception as e:
            logging.error(f"Error fetching user subscriptions: {str(e)}")
            return jsonify({'error': 'Error fetching subscriptions'}), 500
    else:
        logging.error("Unauthorized access attempted to subscriptions")
        return jsonify({'error': 'Unauthorized'}), 401


@app.route('/search', methods=['POST'])
def search_music():
    data = request.get_json()

    title = data.get('title', '')
    artist = data.get('artist', '')
    year = data.get('year', '')

    filter_expression = None
    if title:
        if filter_expression:
            filter_expression &= Attr('title').contains(title)
        else:
            filter_expression = Attr('title').contains(title)
    if artist:
        if filter_expression:
            filter_expression &= Attr('artist').contains(artist)
        else:
            filter_expression = Attr('artist').contains(artist)
    if year:
        if filter_expression:
            filter_expression &= Attr('year').contains(year)
        else:
            filter_expression = Attr('year').contains(year)

    try:
        results = []
        if filter_expression:
            response = music_table.scan(FilterExpression=filter_expression)
            results = response['Items']
        logging.debug(f"Search results: {results}")  # Log the results
        return jsonify(results=results)  # Return results as JSON
    except ClientError as e:
        logging.error(f"Error performing search: {e.response['Error']['Message']}")
        return jsonify({'error': 'Error performing search', 'message': str(e)}), 500

@app.route('/subscribe', methods=['POST'])
def subscribe():
    if 'logged_in' in session:
        email = session.get('email')
        data = request.get_json()
        title = data.get('title')
        artist = data.get('artist')

        if not email or not title or not artist:
            return jsonify({'error': 'Missing title or artist data for subscription.'}), 400

        try:
            response = music_table.update_item(
                Key={
                    'title': title,
                    'artist': artist
                },
                UpdateExpression="SET subscriptions = list_append(if_not_exists(subscriptions, :empty_list), :email)",
                ExpressionAttributeValues={
                    ':email': [email],
                    ':empty_list': [],
                },
                ReturnValues="UPDATED_NEW"
            )
            
            subscribed_music = {
                'title': title,
                'artist': artist,
                'img_url': data.get('img_url')  
            }
            
            return jsonify({'success': 'Subscription added successfully!', 'subscribed_music': subscribed_music}), 200
        except ClientError as e:
            logging.error(f"Error subscribing to music: {e.response['Error']['Message']}")
            return jsonify({'error': f"An error occurred while subscribing to music: {e.response['Error']['Message']}"}), 500
    else:
        return jsonify({'error': 'You must be logged in to subscribe.'}), 401

@app.route('/remove_subscription', methods=['POST'])
def remove_subscription():
    if 'logged_in' in session:
        email = session.get('email')
        data = request.get_json()
        title = data.get('title')
        artist = data.get('artist')

        logging.debug(f"Received removal request for: {title} by {artist} from {email}")

        if not title or not artist:
            logging.debug(f"Missing data: title={title}, artist={artist}")
            logging.error("Missing title or artist in the request data.")
            return jsonify({'error': 'Missing title or artist data.'}), 400

        try:
            # Fetch the current item to get the list of subscriptions
            item_response = music_table.get_item(Key={'title': title, 'artist': artist})
            if 'Item' not in item_response or 'subscriptions' not in item_response['Item']:
                logging.error("No subscriptions found for the item or item does not exist.")
                return jsonify({'error': 'No subscriptions found or item does not exist.'}), 404
            
            subscriptions = item_response['Item']['subscriptions']
            if email not in subscriptions:
                logging.error("Email not subscribed.")
                return jsonify({'error': 'Email not subscribed to this item.'}), 404

            # Determine the index of the email in the subscriptions list
            index_to_remove = subscriptions.index(email)

            # Remove the email using the index
            response = music_table.update_item(
                Key={'title': title, 'artist': artist},
                UpdateExpression=f"REMOVE subscriptions[{index_to_remove}]",
                ReturnValues="UPDATED_NEW"
            )
            logging.info(f"Update response: {response}")
            return jsonify({'success': 'Subscription removed successfully!'}), 200
        except ClientError as e:
            logging.error("DynamoDB client error: " + str(e))
            logging.debug(f"DynamoDB client error details: {e.response['Error']}")
            return jsonify({'error': 'DynamoDB error: ' + str(e)}), 500
        except Exception as e:
            logging.error("General error: " + str(e))
            logging.debug(f"General error details: {e}")
            return jsonify({'error': 'Server error: ' + str(e)}), 500
    else:
        logging.debug("Unauthorized access attempt.")
        logging.error("You must be logged in to subscribe.")
        return jsonify({'error': 'You must be logged in to subscribe.'}), 401




@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    session.pop('subscriptions', None)
    return redirect(url_for('login'))

if __name__ == "__main__":
    app.run(debug=True)