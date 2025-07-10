
from flask import Flask, render_template, request, jsonify
import sqlite3
from datetime import datetime, timedelta

app = Flask(__name__)

def get_db_connection():
    conn = sqlite3.connect('data/data.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index():
    conn = get_db_connection()
    locations = conn.execute('SELECT DISTINCT location_code FROM Sign_Asst').fetchall()
    conn.close()
    return render_template('index.html', locations=[row['location_code'] for row in locations])

@app.route('/get_assets', methods=['POST'])
def get_assets():
    data = request.get_json()
    location = data['location']
    conn = get_db_connection()
    assets = conn.execute(
        'SELECT DISTINCT smms_asset_code FROM Sign_Asst WHERE location_code = ?', (location,)
    ).fetchall()
    conn.close()
    return jsonify({'assets': [row['smms_asset_code'] for row in assets]})

@app.route('/get_signal_data', methods=['POST'])
def get_signal_data():
    data = request.get_json()
    location = data['location']
    asset = data['asset']
    window_index = data.get('window_index', 0)

    conn = get_db_connection()
    vendor_row = conn.execute(
        'SELECT vendor_device_id FROM Sign_Asst WHERE location_code = ? AND smms_asset_code = ?',
        (location, asset)
    ).fetchone()

    if not vendor_row:
        return jsonify({'status': 'nodata', 'message': 'Invalid selection.'})

    vendor_id = vendor_row['vendor_device_id']

    start_time = datetime.strptime("2025-05-30 09:37:14", "%Y-%m-%d %H:%M:%S")
    end_time = datetime.strptime("2025-05-31 01:28:56", "%Y-%m-%d %H:%M:%S")
    interval = timedelta(minutes=30)

    total_windows = int((end_time - start_time) / interval)
    current_index = window_index % total_windows
    current_start = start_time + current_index * interval
    current_end = current_start + interval
    

    rows = conn.execute('''
        SELECT time, vrg, vhg, vdg, vhhg, irg, ihg, idg, ihhg
        FROM SenSglDt_M
        WHERE vendor_device_id = ?
        AND datetime(time) BETWEEN ? AND ?
        ORDER BY datetime(time)
    ''', (vendor_id, current_start, current_end)).fetchall()

    conn.close()

    if not rows:
        return jsonify({'status': 'nodata', 'message': 'No data found for this time window.'})

    asset_prefix = asset[:3].upper() if asset else ""

    thresholds = {
        'LEC': {'vrg': None, 'vhg': None, 'vdg': None, 'vhhg': None,
                'irg': None, 'ihg': None, 'idg': None, 'ihhg': None},
        'LES': {'vrg': None, 'vhg': None, 'vdg': None, 'vhhg': None,
                'irg': None, 'ihg': None, 'idg': None, 'ihhg': None},
        'LED': {'vrg': 85952.370691305402, 'vhg': 12147.030755879988, 'vdg': 13605.321429166320, 'vhhg': 8253.7024069292912468,
                'irg': 106.6308273459334601, 'ihg': 12.4728365599356806, 'idg': 16.6819855084534022, 'ihhg': 8.7291080203214791}
    }

    data_dict = {
        'time': [row['time'] for row in rows],
        'vrg': [row['vrg'] for row in rows],
        'vhg': [row['vhg'] for row in rows],
        'vdg': [row['vdg'] for row in rows],
        'vhhg': [row['vhhg'] for row in rows],
        'irg': [row['irg'] for row in rows],
        'ihg': [row['ihg'] for row in rows],
        'idg': [row['idg'] for row in rows],
        'ihhg': [row['ihhg'] for row in rows],
        'window_index': window_index + 1,
        'asset_prefix': asset_prefix,
        'thresholds': thresholds.get(asset_prefix, {})
    }
    return jsonify(data_dict)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=7500, debug=True)
