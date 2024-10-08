from flask import Flask, request, jsonify
from flask_socketio import SocketIO, join_room, emit, leave_room
from flask_cors import CORS
import hashlib
import db_functions as db_functions
from openai import OpenAI
import os
from dotenv import load_dotenv


app = Flask(__name__)
CORS(app)  
# CORS(app, resources={r"/*": {"origins": "http://localhost:3000"}})
socketio = SocketIO(app, cors_allowed_origins='*')  

load_dotenv()
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
client = OpenAI(api_key=OPENAI_API_KEY)

rooms = {}


difficulty = {
    "master": "The topic should be serious, semi formal, a little longer than the avgerage text message. Topic should not need any extensive previous background.",
    "seasoned": "Topic that are a little more personal, opinionated, and a little less casual in topic. Also, use topics that do not require long responses.Topic should not need any extensive previous background.",
    "novice": "topics that only really need one sentence per response from the user, extremely casual in topic and tone. Topic needs to be not serious. Topic should not need any extensive previous background."
}

def hash_string(string):
    # Create a hash object using SHA-256
    hash_object = hashlib.sha256(string.encode())
    # Convert the hash to a hexadecimal string
    hash_hex = hash_object.hexdigest()
    return hash_hex

# --------------- Sockets ---------------

@socketio.on('create_room')
def handle_create_room(data):
    print("Creating room...\n")
    creator = data['creator']
    room = hash_string(creator)
    print("Room created successfully.\n")
    db_functions.create_lobby(room, data['creator_id'], data['game_mode'], data['difficulty'], data['max_players'])
    players = db_functions.view_lobby(room)
    join_room(room)
    emit('room_created', {'message': f'Room {room} created for {creator}', 'room': room, 'creator': creator, 'players': players}, room=request.sid)

@socketio.on('join_room')
def handle_join_room(data):
    room = data['room']
    user = data['user']
    if db_functions.join_lobby(room, data['user_id']) == -1:
        emit('room_joined', {'message': f'Room {room} is full', 'room': room, 'user': user, 'players': players, 'status': -1}, room=request.sid)
        return
    players = db_functions.view_lobby(room)
    join_room(room)
    print(f'User {user} joined room {room}.')
    emit('room_joined', {'message': f'User joined {room}', 'room': room, 'user': user, 'players': players, 'status': 0}, room=request.sid)
    emit('room_updated', {'message': f'User joined {room}', 'room': room, 'user': user, 'players': players}, room=room)

@socketio.on('leave_room')
def handle_leave_room(data):
    room = data['room']
    user = data['user']
    gameInfo = GameInfo()
    gameInfo.end_game(room)
    db_functions.leave_lobby(room, data['user_id'])
    players = db_functions.view_lobby(room)
    print(players)
    leave_room(room)
    emit('room_updated', {'message': f'User left {room}', 'room': room, 'user': user, 'players': players}, room=room)

@socketio.on('start_room')
def handle_start_room(data):
    room = data['room']
    # TODO HANDLE BACKEND GAME INITIALIZATION
    print("STARTING ROOMOMOOMOMMMMM")
    emit('room_started', {'message': f'Game {room} has started', 'room': room}, room=room)

# --------------- OpenAI Functions ---------------

@app.route('/generate_prompt', methods=['POST'])
def handle_generate_prompt(prompt_diffculty):
    generated_prompt = generate_prompt(prompt_diffculty)
    return jsonify({'generated_text': generated_prompt}), 200

@app.route('/generate_prompt', methods=['POST'])
def handle_ai_response_prompt(previous_conversation, prompt):
    generated_prompt = ai_response_prompt(previous_conversation, prompt)
    return jsonify({'ai_response_text': generated_prompt}), 200


def generate_prompt(prompt_diffculty):
    response = client.chat.completions.create(model="gpt-4",
    messages=[
        {"role": "system", "content": "You are an useful program that will do anything to help the user, making sure you satisfy the user to the best of your abilities"},
        {"role": "user", "content": f"Generate me an conversation topic is likely to show up in people's lives. that is 2 sentences long, that are designed to be graded for english texting fluency, make sure the conversation is engaging and interesting. make it sound as human as possible. {difficulty[prompt_diffculty]}"}
    ])
    return jsonify({"status": "success", "content": response.choices[0].message.content.strip()})

# TODO: check if there could be too many words, might cause crash
@app.route('/ai_response', methods=['POST'])
def ai_response_prompt():
    data = request.json
    previous_conversation = data.get("previous_conversation")
    prompt = data.get("prompt")
    thread_id = data.get("thread_id")
    prev_convo = ""
    is_AI = True
    for convo in previous_conversation:
        if is_AI:
            prev_convo += "you said: "
        else:
            prev_convo += "the other person said: "
        is_AI = not is_AI
        prev_convo += convo["text"] + "\n"
    response = client.chat.completions.create(model="gpt-4",
        messages=[
            {"role": "system", "content": "You are an competent but easy conversation program, you should behave like one, that is trying to have a normal conversation with the user, make sure you best mimic how a normal human would engage in the conversation."},
            {"role": "user", "content": f"The starting conversation topic is {prompt}. Here's the previous conversation that has been talked about so far: {prev_convo}. Generate me the a starting piece to this prompt like an online text conversation, try to come up with personalized example based on the prompt, include that in the first reponse, keep the responses between 1 to 2 sentences, only include what you say to the person in the response."}
    ])
    message_id = db_functions.generate_new_message_id()
    db_functions.send_message(message_id, "1", thread_id, response.choices[0].message.content.strip())
    return jsonify({"status": "success", "content": response.choices[0].message.content.strip()})

@app.route('/ai_grade', methods=['POST'])
def grade_user_responses():
    data = request.json
    previous_conversation = data.get("previous_conversation")
    prompt = data.get("prompt")
    game_id = data.get("game_id")
    message_id = data.get("message_id")
    user_id = data.get("user_id")

    print(data)

    prev_convo = ""
    is_AI = True
    for convo in previous_conversation:
        if is_AI:
            prev_convo += "you said: "
        else:
            prev_convo += "the other person said: "
        is_AI = not is_AI
        prev_convo += convo["text"] + "\n"

    print(prev_convo)

    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a competent grading program that has no bias. You should behave like one. Make sure you take into account how a normal human would engage in the conversation."},
            {"role": "user", "content": f"The starting conversation topic is {prompt}. Here's the previous conversation that has been talked about so far: {prev_convo}. Focusing on the latest response from the other person, give me a grade out of 100 for the following: Flow, Conciseness, Clarity, and On Topic. Please provide the grades in the following format, don't include any puntucation except : and , : Flow: [number], Conciseness: [number], Clarity: [number], Relevance: [number]"}
        ]
    )
    
    response_text = response.choices[0].message.content.strip()
    print(response_text)
    
    # Extract the numbers from the response
    grades = {}
    for line in response_text.split('\n'):
        if ':' in line:
            for small_part in line.split(","):
                smaller_part = small_part.split(":")
                grades[smaller_part[0].strip()] = int(smaller_part[1].strip())
    print("here:" , grades)
    db_functions.add_game_score(user_id, game_id, message_id, grades["Flow"], grades["Conciseness"], grades["Clarity"], grades["Relevance"])
    return jsonify({"status": "success"} | grades)


@app.route('/send_message', methods=['POST'])
def send_message():
    data = request.json
    user_id = data.get('user_id')
    thread_id = data.get('thread_id')
    content = data.get('content')
    print("I am at least here 2")
    if not user_id or not thread_id or not content:
        return jsonify({"error": "Missing required parameters"}), 400

    # Generate a new message_id
    message_id = db_functions.generate_new_message_id()
    if message_id is None:
        return jsonify({"error": "Failed to generate message_id"}), 500

    try:
        db_functions.send_message(message_id, user_id, thread_id, content)
        return jsonify({"status": "success", "message_id": message_id})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --------------- SignUp / Login Functions ---------------

@app.route('/signup', methods=['POST'])
def signup():
    data = request.json
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    randomStringId = username + "lovestext"
    return jsonify(db_functions.create_user(randomStringId, username, email, password))

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    return jsonify(db_functions.login_user(username, password))

@app.route('/get_user_stats', methods=['POST'])
def get_user_stats():
    data = request.json
    user_id = data.get('user_id')
    return jsonify(db_functions.get_user_stats(user_id))

@app.route('/create_user_stats', methods=['POST'])
def handle_create_user_stats(user_id, games_played, time_played, games_won, games_lost, global_ranking, gems, coins):
    try:
        db_functions.create_user_stats(user_id, games_played, time_played, games_won, games_lost, global_ranking, gems, coins)
        return jsonify({"message": "Created user stats successfully"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route('/create_user_leaderboard', methods=['POST'])
def handle_create_user_leaderboard(user_id, elo):
    try:
        db_functions.create_user_leaderboard(user_id, elo)
        return jsonify({"message": "Created user stats successfully"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/get_elo', methods=['POST'])
def handle_get_elo(user_id):
    try:
        db_functions.get_elok(user_id)
        return jsonify({"message": "Got elo successfully"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/get_global_rank', methods=['POST'])
def handle_get_global_rank(user_id):
    try:
        db_functions.get_global_rank(user_id)
        return jsonify({"message": "Got global rank successfully"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/insert_mission', methods=['POST'])
def handle_insert_mission():
    try:
        db_functions.insert_mission()
        return jsonify({"message": "Inserted mission successfully"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route('/reset_daily_missions', methods=['POST'])
def handle_reset_daily_missions():
    try:
        db_functions.reset_daily_missions()
        return jsonify({"message": "Reseted daily missions successfully"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route('/reset_user_daily_completion', methods=['POST'])
def handle_reset_user_daily_completion():
    try:
        db_functions.reset_user_daily_completion()
        return jsonify({"message": "Reseted user daily completion successfully"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
# @app.route('/create_thread', methods=['POST'])
# def handle_create_thread():
#     try:
#         data = request.json
#         thread_name = data['thread_name']
#         thread_id = db_functions.generate_new_thread_id()
#         # db_functions.create_thread(thread_id, thread_name)
#         return jsonify(thread_id), 201
#     except Exception as e:
#         return jsonify({"error": str(e)}), 500
    
@app.route('/send_message', methods=['POST'])
def handle_send_message(message_id, user_id, thread_id, content):
    try:
        db_functions.send_message(message_id, user_id, thread_id, content)
        return jsonify({"message": "Sent message successfully"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route('/retrieve_messages', methods=['POST'])
def handle_retrieve_messages(thread_id):
    try:
        db_functions.retrieve_messages(thread_id)
        return jsonify({"message": "Retrieved messages successfully"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/create_game', methods=['POST'])
def create_game():
    data = request.json
    match_id = data['match_id']
    player_list = data['player_list']
    game_info = GameInfo()
    game = game_info.create_game(match_id, player_list)
    return jsonify({'message': 'Game created', 'game': game})


@app.route('/api/end_game', methods=['POST'])
def end_game():
    match_id = request.json['match_id']
    game_info = GameInfo()
    game_info.end_game(match_id)
    return jsonify({'message': 'Game ended'})

@app.route('/api/get_lobbies', methods=['GET'])
def get_lobbies():
    return jsonify({"lobbies": db_functions.get_lobbies()})

@app.route('/api/get_lobby', methods=['POST'])
def get_lobby():
    data = request.json()
    lobby_id = data.get('lobby_id')
    return jsonify({"lobbies": db_functions.get_lobby(lobby_id)})


# --------------- Thread Functions ---------------

@app.route('/create_thread', methods=['POST'])
def make_thread():
    try:
        thread_name = "test_thread"
        thread_info = []
        db_functions.create_thread(thread_info, thread_name)
        thread_id = thread_info[0]
        
        return jsonify({"thread_id": thread_id}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500
  

# --------------- Score Functions ---------------

@app.route('/api/update_score', methods=['POST'])
def update_score():
    data = request.json
    match_id = data['match_id']
    userID = data['userID']
    new_scores = data['new_scores']
    try:
        game_info = GameInfo()
        game_info.update_score(match_id, userID, new_scores)
        response = jsonify({'message': 'Score updated successfully'})
        response.status_code = 200
    except Exception as e:
        response = jsonify({'error': str(e)})
        response.status_code = 500
    return jsonify({'message': 'Score updated'})

@app.route('/api/get_scoreboard', methods=['POST'])
def get_leaderboard():
    data = request.json
    match_id = data.get('id')
    if not match_id:
        return jsonify({'error': 'match_id is required'}), 400

    try:
        game_info = GameInfo()
        res = game_info.get_scoreboard(match_id)

        return jsonify(res)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
@app.route('/api/find_progress_percentage', methods=['POST'])
def find_percentage():
    data = request.json
    match_id = data.get('match_id')
    userID = data.get('user_id')
    if not match_id:
        return jsonify({'error': 'match_id is required'}), 400

    try:
        game_info = GameInfo()
        res = game_info.find_progress_percentage(match_id, userID)
        return jsonify(res)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


GameLeaderBoards = {}

# {'chinatown': {'user1': {'Flow': 0, 'Conciseness': 0, 'Clarity': 0, 'Relevance': 0, 'prompt_count': 0} }}

class GameInfo:
    def get_scoreboard(self, match_id):
        player_list = db_functions.view_lobby(match_id)
        print("\n\n\n\n")
        print(player_list)
        
        if match_id not in GameLeaderBoards:
            GameLeaderBoards[match_id] = {}
        
        # Remove players who are not in player_list
        for player in list(GameLeaderBoards[match_id].keys()):
            if player not in player_list:
                del GameLeaderBoards[match_id][player]
        
        # Add new players to the leaderboard with a score of 0
        for player in player_list:
            if player not in GameLeaderBoards[match_id]:
                GameLeaderBoards[match_id][player] = {'Flow': 0, 'Conciseness': 0, 'Clarity': 0, 'Relevance': 0, 'prompt_count': 0}
        
        return self._get_total_scores(GameLeaderBoards[match_id])
        
    def update_score(self,match_id, userID, new_scores):
        print("\n\n\n\n new_scores", new_scores)
        print('asdf')
        username = db_functions.user_id_to_username(userID)
        GameLeaderBoards[match_id][username]['prompt_count'] += 1
        print("niggers")
        for key in new_scores.keys():
            if key != 'status':
                GameLeaderBoards[match_id][username][key] += new_scores[key]
        # GameLeaderBoards[match_id][username] += new_scores['Flow'] + new_scores['Conciseness'] + new_scores['Clarity'] + new_scores['Relevance']
        # print("match_id", match_id)
        # print("userID", userID)
        print(GameLeaderBoards)

    def find_progress_percentage(self, match_id, userID):
        username = db_functions.user_id_to_username(userID)
        percentages = {}
        print(GameLeaderBoards[match_id][username]['prompt_count'])
        for key in GameLeaderBoards[match_id][username].keys():
            if key != 'prompt_count':
                percentages[key] = GameLeaderBoards[match_id][username][key] / GameLeaderBoards[match_id][username]['prompt_count']

        return percentages
    
    def end_game(self, match_id):
        if match_id in GameLeaderBoards:
            del GameLeaderBoards[match_id]

    def _get_total_scores(self, score_dictionary):
        try:
            res = []
            for player in score_dictionary:
                print(score_dictionary[player])
                player_score = 0
                for key in score_dictionary[player].keys():
                    if key != 'prompt_count':
                        player_score += score_dictionary[player][key]

                res.append([player, player_score])
            
            res.sort(key=lambda x: x[1], reverse=True)
            return res
        
        except Exception as e:
            return [["Error", str(e)]]


if __name__ == '__main__':
    socketio.run(app, port=5000, debug=True)
    # g = GameInfo()
    # print(g.get_scoreboard('chinatown'))

    # print(g.get_scoreboard('chinatown'))
    # print(g.get_scoreboard('chinatown'))

    # print(db_functions.create_thread(11, 'test'))
    # print(db_functions.generate_new_thread_id())