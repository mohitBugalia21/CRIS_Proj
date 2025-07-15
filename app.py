# from flask import Flask, render_template, request, jsonify
# import sqlite3
# from datetime import datetime, timedelta

# app = Flask(__name__)

# def get_db_connection():
#     conn = sqlite3.connect('data/data.db')
#     conn.row_factory = sqlite3.Row
#     return conn

# @app.route('/')
# def index():
#     conn = get_db_connection()
#     locations = conn.execute('SELECT DISTINCT location_code FROM Sign_Asst').fetchall()
#     conn.close()
#     return render_template('index.html', locations=[row['location_code'] for row in locations])

# @app.route('/get_assets', methods=['POST'])
# def get_assets():
#     data = request.get_json()
#     location = data['location']
#     conn = get_db_connection()
#     assets = conn.execute(
#         'SELECT DISTINCT smms_asset_code FROM Sign_Asst WHERE location_code = ?', (location,)
#     ).fetchall()
#     conn.close()
#     return jsonify({'assets': [row['smms_asset_code'] for row in assets]})

# @app.route('/get_signal_data', methods=['POST'])
# def get_signal_data():
#     data = request.get_json()
#     location = data['location']
#     asset = data['asset']
#     window_index = data.get('window_index', 0)

#     conn = get_db_connection()
#     vendor_row = conn.execute(
#         'SELECT vendor_device_id FROM Sign_Asst WHERE location_code = ? AND smms_asset_code = ?',
#         (location, asset)
#     ).fetchone()

#     if not vendor_row:
#         return jsonify({'status': 'nodata', 'message': 'Invalid selection.'})

#     vendor_id = vendor_row['vendor_device_id']

#     start_time = datetime.strptime("2025-05-30 09:37:14", "%Y-%m-%d %H:%M:%S")
#     end_time = datetime.strptime("2025-05-31 01:28:56", "%Y-%m-%d %H:%M:%S")
#     interval = timedelta(minutes=30)

#     total_windows = int((end_time - start_time) / interval)
#     current_index = window_index % total_windows
#     current_start = start_time + current_index * interval
#     current_end = current_start + interval

#     rows = conn.execute('''
#         SELECT time, vrg, vhg, vdg, vhhg, irg, ihg, idg, ihhg
#         FROM SenSglDt_M
#         WHERE vendor_device_id = ?
#         AND datetime(time) BETWEEN ? AND ?
#         ORDER BY datetime(time)
#     ''', (vendor_id, current_start, current_end)).fetchall()

#     conn.close()

#     if not rows:
#         return jsonify({'status': 'nodata', 'message': 'No data found for this time window.'})

#     asset_prefix = asset[:3].upper() if asset else ""

#     # Example thresholds (to be filled/edited manually)
#     thresholds = {
#         'LEC': {'vrg': None, 'vhg': None, 'vdg': None, 'vhhg': None,
#                 'irg': None, 'ihg': None, 'idg': None, 'ihhg': None},
#         'LES': {'vrg': None, 'vhg': None, 'vdg': None, 'vhhg': None,
#                 'irg': None, 'ihg': None, 'idg': None, 'ihhg': None},
#         'LED': {'vrg': 85952.37, 'vhg': 12147.03, 'vdg': 13605.32, 'vhhg': 8253.70,
#                 'irg': 106.63, 'ihg': 12.47, 'idg': 16.68, 'ihhg': 8.72}
#     }

#     # Organize graph data
#     signal_keys = ['vrg', 'vhg', 'vdg', 'vhhg', 'irg', 'ihg', 'idg', 'ihhg']
#     data_dict = {
#         'time': [row['time'] for row in rows],
#         'window_index': window_index + 1,
#         'asset_prefix': asset_prefix,
#         'thresholds': thresholds.get(asset_prefix, {})
#     }

#     # Include signal data and compute max values for each key
#     for key in signal_keys:
#         values = [row[key] for row in rows if row[key] is not None]
#         data_dict[key] = values
#         if values:
#             data_dict[f'max_{key}'] = max(values)
#         else:
#             data_dict[f'max_{key}'] = 0

#     return jsonify(data_dict)

# if __name__ == "__main__":
#     app.run(debug=True, port=7000)


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

    # Filter data ≥ 5000
    rows = conn.execute('''
    SELECT time, vrg, vhg, vdg, vhhg, irg, ihg, idg, ihhg
    FROM SenSglDt_M
    WHERE vendor_device_id = ?
    AND datetime(time) BETWEEN ? AND ?
    AND (
        vrg >= 5000 OR vhg >= 5000 OR vdg >= 5000 OR vhhg >= 5000 OR
        irg >= 5000 OR ihg >= 5000 OR idg >= 5000 OR ihhg >= 5000
    )
    ORDER BY datetime(time)
    ''', (vendor_id, current_start, current_end)).fetchall()

    if not rows:
    # 🟡 Auto-skip to next window instead of stopping
        return jsonify({'status': 'nodata', 'window_index': window_index + 1})


    # Prepare response data
    keys = ['vrg', 'vhg', 'vdg', 'vhhg', 'irg', 'ihg', 'idg', 'ihhg']
    data_dict = {'time': [], 'window_index': window_index + 1}
    max_values = {}

    for key in keys:
        data_dict[key] = []

    for row in rows:
        data_dict['time'].append(row['time'])
        for key in keys:
            value = row[key]
            data_dict[key].append(value)

    # Compute max values (for Y-axis limit)
    for key in keys:
        values = [v for v in data_dict[key] if v is not None]
        max_val = max(values) if values else 0
        max_values[key] = max_val + 20000  # Y-axis padding

    # Add threshold logic dictionary (null by default, you will fill later)
    asset_prefix = asset[:3].upper()
    thresholds = {
        'LEC': {'vrg': None, 'vhg': None, 'vdg': None, 'vhhg': None,
                'irg': None, 'ihg': None, 'idg': None, 'ihhg': None},
        'LES': {'vrg': None, 'vhg': None, 'vdg': None, 'vhhg': None,
                'irg': None, 'ihg': None, 'idg': None, 'ihhg': None},
        'LED': {'vrg': 85952.37, 'vhg': 12147.03, 'vdg': 13605.32, 'vhhg': 8253.70,
                'irg': 106.63, 'ihg': 12.47, 'idg': 16.68, 'ihhg': 8.72}
    }

    data_dict['asset_prefix'] = asset_prefix
    data_dict['thresholds'] = thresholds.get(asset_prefix, {})
    data_dict['max_values'] = max_values

    return jsonify(data_dict)

if __name__ == "__main__":
    app.run(debug=True, port=7500)

