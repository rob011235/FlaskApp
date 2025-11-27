from flask import Flask,  render_template, flash, request, jsonify
from bike_calc import calc_bike_rentals
import logging, io, os, sys, base64, datetime
from datetime import timedelta
import pandas as pd
import numpy as np
from sklearn.ensemble import GradientBoostingClassifier
import scipy
import pickle
import os
from ollama import Client


from datetime import timedelta

# global variables
crime_horizon_df = None
src = 'static/data/sf-crime-horizon.csv'

app = Flask(__name__)

# load in pre-trained model
global gbm_model
gbm_model = pickle.load(open('static/pickles/gbm_model_dump.p', 'rb'))
features = ['fixed acidity',
        	 'volatile acidity',
        	 'citric acid',
        	 'residual sugar',
        	 'chlorides',
        	 'free sulfur dioxide',
        	 'total sulfur dioxide',
        	 'density',
        	 'pH',
        	 'sulphates',
        	 'alcohol',
        	 'color']
# variables for up-down app
# default traveler constants
DEFAULT_BUDGET = 10000
TRADING_DAYS_LOOP_BACK = 90
INDEX_SYMBOL = ['^DJI']
STOCK_SYMBOLS = ['BA','GS','UNH','MMM','HD','AAPL','MCD','IBM','CAT','TRV']
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Get Stock Data
global stock_data_df
stock_data_df = pd.read_pickle(os.path.join(BASE_DIR, 'static/pickles/stock_data.pkl'))
print("Stock data read with shape: ", stock_data_df.head())

def LoadCrimeHorizon():
    from numpy import genfromtxt
    crime_horizon_df = genfromtxt(src, delimiter=',', names = True, dtype = None,)
    return crime_horizon_df

crime_horizon_df = LoadCrimeHorizon()

def GetCrimeEstimates(horizon_date, horizon_time_segment):
    Day_of_month = int(horizon_date.split('/')[1])
    Month_of_year = int(horizon_date.split('/')[0])
    Day_Segment = int(horizon_time_segment) # 0,1,2
    crime_horizon_df_tmp = crime_horizon_df[(crime_horizon_df['Day_of_month'] == Day_of_month) & 
                                            (crime_horizon_df['Month_of_year']==Month_of_year) &
                                            (crime_horizon_df['Day_Segment'] == Day_Segment)]


    
    # build latlng string for google maps
    LatLngString = ''
    for lat, lon in zip(crime_horizon_df_tmp['Latitude'], crime_horizon_df_tmp['Longitude']): 
        LatLngString += "new google.maps.LatLng(" + str(lat) + "," + str(lon) + "),"
     
    return (LatLngString)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/bike_calc")
def bike_calc():
    return render_template("bike_calc.html")

@app.route("/calculate", methods=['POST'])
def calculate():
    holiday = request.form.get("isHoliday") == "on"
    season = int(request.form.get("season"))
    temp = float(request.form.get("temp"))
    bike_rentals = calc_bike_rentals(holiday, season, temp)
    return render_template("results.html", rentals=bike_rentals)

@app.route("/wine_calc", methods=['POST','GET'])
def wine_calc():
    return render_template("wine_calc.html", quality_prediction=1, image_name='/static/images/wine_red_6.jpg')

def get_wine_image_to_show(wine_color, wine_quality):
    if wine_color == 0:
        wine_color_str = 'white'
    else:
        wine_color_str = 'red'
    return('/static/images/wine_' + wine_color_str + '_' + str(wine_quality) + '.jpg')

@app.route("/background_proccess", methods=['POST','GET'])
def background_process():
    fixed_acidity = float(request.args.get('fixed_acidity'))
    volatile_acidity = float(request.args.get('volatile_acidity'))
    citric_acid = float(request.args.get('citric_acid'))
    residual_sugar = float(request.args.get('residual_sugar'))
    chlorides = float(request.args.get('chlorides'))
    free_sulfur_dioxide = float(request.args.get('free_sulfur_dioxide'))
    total_sulfur_dioxide = float(request.args.get('total_sulfur_dioxide'))
    density = float(request.args.get('density'))
    pH = float(request.args.get('pH'))
    sulphates = float(request.args.get('sulphates'))
    alcohol = float(request.args.get('alcohol'))
    color = int(request.args.get('color'))

	# create data set of new data
    x_test_tmp = pd.DataFrame([[fixed_acidity,
        volatile_acidity,
        citric_acid,
        residual_sugar,
        chlorides,
        free_sulfur_dioxide,
        total_sulfur_dioxide,
        density,
        pH,
        sulphates,
        alcohol,
        color]], columns = features)

	# predict quality based on incoming values
    preds = gbm_model.predict_proba(x_test_tmp[features])

	# get best quality prediction from original quality scale
    predicted_quality = [3,6,9][np.argmax(preds[0])]
    return jsonify({'quality_prediction':predicted_quality, 'image_name': get_wine_image_to_show(color, predicted_quality)})

@app.route("/bootstrap_demo")
def bootstrap_demo():
    return render_template("bootstrap_demo.html")


@app.route("/pair_trading_demo", methods=['POST', 'GET'])
def get_pair_trade():
    if request.method == 'POST':
        selected_budget = request.form.get('selected_budget')
        if selected_budget == "":
            selected_budget = DEFAULT_BUDGET
        
		# calculate widest spread
        stock1 = '^DJI'
        last_distance_from_index = {}
        temp_series1 = stock_data_df[stock1].pct_change().cumsum()
        for stock2 in list(stock_data_df):
            # no need to process itself
            if (stock2 != stock1):
                temp_series2 = stock_data_df[stock2].pct_change().cumsum()
                # we are subtracting the stock minus the index, if stock is strong compared
                # to index, we assume a postive value
                diff = list(temp_series2 - temp_series1)
                last_distance_from_index[stock2] = diff[-1]
        weakest_symbol = min(last_distance_from_index.items(), key=lambda x: x[1])
        strongest_symbol = max(last_distance_from_index.items(), key=lambda x: x[1])
		
		# budget trade size
        short_symbol = strongest_symbol[0]
        short_last_close = stock_data_df[strongest_symbol[0]][-1]

        long_symbol = weakest_symbol[0]
        long_last_close = stock_data_df[weakest_symbol[0]][-1]

        return render_template('pair_trading_demo.html',
            short_symbol = short_symbol,
            long_symbol = long_symbol,
            short_last_close = round(short_last_close,2),
            short_size = round((float(selected_budget) * 0.5) / short_last_close,2),
            long_last_close = round(long_last_close,2),
            long_size = round((float(selected_budget) * 0.5) / long_last_close,2),
            selected_budget = selected_budget)
    else:
        return render_template('pair_trading_demo.html',
        	short_symbol = "None",	
        	long_symbol = "None",
        	short_last_close = 0,
        	short_size = 0,
        	long_last_close = 0,
        	long_size = 0,
        	selected_budget = DEFAULT_BUDGET)

@app.route("/crime_map",methods=['POST','GET'])
def crime_map():
    if request.method == 'POST': # Post view

            horizon_date_int = int(request.form.get('slider_crime_horizon'))
            # offering 3 months horizon over 270 points - 3 per day to account for time segments
            date_int = int(horizon_date_int / 3)
            time_segment_int = int(horizon_date_int % 3)

            if (time_segment_int == 0):
                image_source = 'static/images/morning.jpg'
            elif (time_segment_int == 1):
                image_source = 'static/images/afternoon.jpg'
            else:
                image_source = 'static/images/night.jpg'


            date_horizon = datetime.datetime.today() + timedelta(days=date_int)

            return render_template('crime_map.html',
                date_horizon = date_horizon.strftime('%m/%d/%Y'),
                time_segment_int = time_segment_int, 
                crime_horizon = GetCrimeEstimates(date_horizon.strftime('%m/%d/%Y'), time_segment_int),
                current_value=horizon_date_int,
                image_source=image_source)
    else: # Get view
        return render_template("crime_map.html",
                date_horizon = datetime.datetime.today().strftime('%m/%d/%Y'),
                time_segment_int = 0, 
                crime_horizon = '',
                current_value=0,
                image_source='static/images/morning.jpg')

@app.route("/olama",methods=['POST','GET'])
def olama():
    if request.method == 'POST':
        print("Received POST request    for Olama")
        prompt = request.form.get('olama_prompt')
        print("Prompt: ", prompt)
        client = Client(
            host='https://ollama.com',
            headers={'Authorization': 'Bearer 1b9a19ff7e564536b4af41a1a9809362.KBhabQ_vinpyhSgd5zixYf44'}
        )

        messages = [
        {
            'role': 'user',
            'content': prompt,
        },
        ]
        answer = ''
        for part in client.chat('gpt-oss:120b', messages=messages, stream=True):
            answer += part.message.content
            print(part.message.content, end='', flush=True)
        return render_template("olama.html", answer=answer)
    else:
        return render_template("olama.html")

if __name__ == "__main__":
    print('Starting Flask App')
    app.run(debug=True)