
from flask import Flask, render_template, request, jsonify
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta
import json
import logging

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Database configuration
DB_HOST = "localhost"
DB_PORT = "5432"
DB_NAME = "smms_db"
DB_USER = "postgres"
DB_PASSWORD = "210009"

def get_db_connection():
    """Get PostgreSQL database connection"""
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            cursor_factory=RealDictCursor
        )
        return conn
    except psycopg2.Error as e:
        logger.error(f"Error connecting to database: {e}")
        return None

@app.route('/')
def index():
    conn = get_db_connection()
    if not conn:
        return "Database connection failed", 500
    
    try:
        cursor = conn.cursor()
        # Updated query to match your database structure
        cursor.execute('SELECT DISTINCT location_code FROM public.sensor_asset')
        locations = cursor.fetchall()
        cursor.close()
        conn.close()
        
        location_list = [row['location_code'] for row in locations if row['location_code']] # type: ignore
        logger.info(f"Found {len(location_list)} locations: {location_list}")
        return render_template('index.html', locations=location_list)
    except psycopg2.Error as e:
        logger.error(f"Database error in index: {e}")
        if conn:
            conn.close()
        return "Database error", 500

@app.route('/get_assets', methods=['POST'])
def get_assets():
    try:
        data = request.get_json()
        if not data or 'location' not in data:
            return jsonify({'error': 'Invalid request data'}), 400
            
        location = data['location']
        logger.info(f"Fetching assets for location: {location}")
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = conn.cursor()
        cursor.execute(
            'SELECT DISTINCT smms_asset_code FROM public.sensor_asset WHERE location_code = %s AND smms_asset_code IS NOT NULL',
            (location,)
        )
        assets = cursor.fetchall()
        cursor.close()
        conn.close()
        
        if not assets:
            logger.warning(f"No assets found for location: {location}")
            return jsonify({'assets': [], 'message': 'No assets found for this location'})
        asset_list = [row['smms_asset_code'] for row in assets if row['smms_asset_code']] # type: ignore
        logger.info(f"Found {len(asset_list)} assets: {asset_list}")
        return jsonify({'assets': asset_list})
        
    except psycopg2.Error as e:
        logger.error(f"Database error in get_assets: {e}")
        if conn:
            conn.close()
        return jsonify({'error': 'Database error'}), 500
    except Exception as e:
        logger.error(f"General error in get_assets: {e}")
        return jsonify({'error': 'Server error'}), 500
    
@app.route('/get_locations', methods=['GET'])
def get_locations():
    conn = get_db_connection()
    if not conn:
        return jsonify({'locations': [], 'error': 'Database connection failed'}), 500
    try:
        cursor = conn.cursor()
        cursor.execute('SELECT DISTINCT location_code FROM public.sensor_asset')
        locations = cursor.fetchall()
        cursor.close()
        conn.close()
        location_list = [row['location_code'] for row in locations if row['location_code']] # type: ignore
        logger.info(f"API: Found {len(location_list)} locations: {location_list}")
        return jsonify({'locations': location_list})
    except psycopg2.Error as e:
        logger.error(f"Database error in get_locations: {e}")
        if conn:
            conn.close()
        return jsonify({'locations': [], 'error': 'Database error'}), 500

@app.route('/get_signal_data', methods=['POST'])
def get_signal_data():
    try:
        data = request.get_json()
        if not data or 'location' not in data or 'asset' not in data:
            return jsonify({'status': 'error', 'message': 'Invalid request data'})
            
        location = data['location']
        asset = data['asset']
        window_index = data.get('window_index', 0)
        
        logger.info(f"Fetching signal data for location: {location}, asset: {asset}, window: {window_index}")

        conn = get_db_connection()
        if not conn:
            return jsonify({'status': 'error', 'message': 'Database connection failed'})

        cursor = conn.cursor()
        
        # Get vendor_device_id
        cursor.execute(
            'SELECT vendor_device_id FROM public.sensor_asset WHERE location_code = %s AND smms_asset_code = %s',
            (location, asset)
        )
        vendor_row = cursor.fetchone()

        if not vendor_row or not vendor_row['vendor_device_id']: # type: ignore
            cursor.close()
            conn.close()
            logger.warning(f"No vendor_device_id found for location: {location}, asset: {asset}")
            return jsonify({'status': 'nodata', 'message': 'Invalid selection or no vendor device ID found.'})

        vendor_id = vendor_row['vendor_device_id'] # type: ignore
        logger.info(f"Found vendor_device_id: {vendor_id}")

        # First, let's check what data is available
        cursor.execute(
            'SELECT MIN(time) as min_time, MAX(time) as max_time, COUNT(*) as total_count FROM public.sensor_signal_data WHERE vendor_device_id = %s',
            (vendor_id,)
        )
        time_info = cursor.fetchone()
        logger.info(f"Time range info: {time_info}")

        # If no data exists, return error
        if not time_info or time_info['total_count'] == 0: # type: ignore
            cursor.close()
            conn.close()
            return jsonify({'status': 'nodata', 'message': 'No data found for this asset'})

        # Use actual data time range instead of hardcoded values
        if time_info['min_time'] and time_info['max_time']: # type: ignore
            start_time = time_info['min_time'] # type: ignore
            end_time = time_info['max_time'] # type: ignore
            
            # Calculate total duration and create 30-minute windows
            total_duration = end_time - start_time
            interval = timedelta(minutes=30)
            
            # Calculate total windows
            total_windows = max(1, int(total_duration / interval))
            
            # Calculate current window times
            current_index = window_index % total_windows
            current_start = start_time + current_index * interval
            current_end = min(current_start + interval, end_time)
            
            logger.info(f"Window {current_index + 1}/{total_windows}: {current_start} to {current_end}")
        else:
            # Fallback to your original hardcoded times
            start_time = datetime.strptime("2025-07-14 00:31:27", "%Y-%m-%d %H:%M:%S")
            end_time = datetime.strptime("2025-07-14 06:58:04", "%Y-%m-%d %H:%M:%S")
            interval = timedelta(minutes=30)
            total_windows = max(1, int((end_time - start_time) / interval))
            current_index = window_index % total_windows
            current_start = start_time + current_index * interval
            current_end = current_start + interval


        # Query signal data with more flexible filtering
        cursor.execute('''
            SELECT time, vrg, vhg, vdg, vhhg, irg, ihg, idg, ihhg
            FROM public.sensor_signal_data
            WHERE vendor_device_id = %s
            AND time BETWEEN %s AND %s
            ORDER BY time
        ''', (vendor_id, current_start, current_end))
        rows = cursor.fetchall()
        logger.info(f"Found {len(rows)} rows in time window")

        # If no data in current window, fallback to all data for asset
        if not rows:
            logger.warning(f"No data found in window {current_start} to {current_end}, trying all data for asset {asset}")
            cursor.execute('''
                SELECT time, vrg, vhg, vdg, vhhg, irg, ihg, idg, ihhg
                FROM public.sensor_signal_data
                WHERE vendor_device_id = %s
                ORDER BY time
            ''', (vendor_id,))
            rows = cursor.fetchall()
            logger.info(f"Fallback: Found {len(rows)} rows for all time for asset {asset}")
            if not rows:
                cursor.close()
                conn.close()
                return jsonify({'status': 'nodata', 'message': 'No signal data found for this asset'})

        cursor.close()
        conn.close()

        # Process the data
        asset_prefix = asset[:3].upper() if asset else ""

        # Define thresholds based on asset prefix
        thresholds = {
            'LEC': {'vrg': None, 'vhg': None, 'vdg': None, 'vhhg': None,
                    'irg': None, 'ihg': None, 'idg': None, 'ihhg': None},
            'LES': {'vrg': None, 'vhg': None, 'vdg': None, 'vhhg': None,
                    'irg': None, 'ihg': None, 'idg': None, 'ihhg': None},
            'LED': {'vrg': 85952.370691305402, 'vhg': 12147.030755879988, 'vdg': 13605.321429166320, 'vhhg': 8253.7024069292912468,
                    'irg': 106.6308273459334601, 'ihg': 12.4728365599356806, 'idg': 16.6819855084534022, 'ihhg': 8.7291080203214791}
        }

        # Calculate max values for each signal for proper y-axis scaling
        signal_keys = ['vrg', 'vhg', 'vdg', 'vhhg', 'irg', 'ihg', 'idg', 'ihhg']
        max_values = {}
        
        for key in signal_keys:
            values = []
            for row in rows:
                val = row[key] # type: ignore
                if val is not None and val != '' and isinstance(val, (int, float)):
                    values.append(float(val))
            
            if values:
                max_values[key] = max(values) * 1.1  # Add 10% padding
            else:
                max_values[key] = 100000  # Default fallback

        # Format time for JavaScript
        formatted_times = []
        for row in rows:
            if isinstance(row['time'], datetime): # type: ignore
                formatted_times.append(row['time'].strftime('%Y-%m-%d %H:%M:%S')) # type: ignore
            else:
                formatted_times.append(str(row['time'])) # type: ignore

        # Convert data to proper format
        data_dict = {
            'status': 'success',
            'time': formatted_times,
            'vrg': [float(row['vrg']) if row['vrg'] is not None else None for row in rows], # type: ignore
            'vhg': [float(row['vhg']) if row['vhg'] is not None else None for row in rows], # type: ignore
            'vdg': [float(row['vdg']) if row['vdg'] is not None else None for row in rows], # type: ignore
            'vhhg': [float(row['vhhg']) if row['vhhg'] is not None else None for row in rows], # type: ignore
            'irg': [float(row['irg']) if row['irg'] is not None else None for row in rows], # type: ignore
            'ihg': [float(row['ihg']) if row['ihg'] is not None else None for row in rows], # type: ignore
            'idg': [float(row['idg']) if row['idg'] is not None else None for row in rows], # type: ignore
            'ihhg': [float(row['ihhg']) if row['ihhg'] is not None else None for row in rows], # type: ignore
            'window_index': window_index + 1,
            'asset_prefix': asset_prefix,
            'thresholds': thresholds.get(asset_prefix, {}),
            'max_values': max_values,
            'total_windows': total_windows,
            'current_window': current_index + 1,
            'time_range': f"{current_start.strftime('%H:%M:%S')} - {current_end.strftime('%H:%M:%S')}"
        }
        
        logger.info(f"Returning data with {len(formatted_times)} data points")
        return jsonify(data_dict)

    except psycopg2.Error as e:
        logger.error(f"Database error in get_signal_data: {e}")
        if 'conn' in locals() and conn:
            conn.close()
        return jsonify({'status': 'error', 'message': f'Database error: {str(e)}'})
    except Exception as e:
        logger.error(f"General error in get_signal_data: {e}")
        return jsonify({'status': 'error', 'message': f'Server error: {str(e)}'})

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == "__main__":
    # Test database connection on startup
    test_conn = get_db_connection()
    if test_conn:
        print("✅ Connected to the database successfully.")
        try:
            cursor = test_conn.cursor()
            cursor.execute("SELECT version();")
            db_version = cursor.fetchone()
            print(f"📊 Database version: {db_version[0]}") # type: ignore
            
            # Test sensor_asset table
            cursor.execute("SELECT COUNT(*) FROM public.sensor_asset")
            asset_count = cursor.fetchone()
            print(f"📊 Total assets in database: {asset_count[0]}") # type: ignore
            
            # Test sensor_signal_data table
            cursor.execute("SELECT COUNT(*) FROM public.sensor_signal_data")
            signal_count = cursor.fetchone()
            print(f"📊 Total signal records: {signal_count[0]}") # type: ignore
            
            cursor.close()
        except Exception as e:
            print(f"⚠️  Warning: Could not fetch database info: {e}")
        finally:
            test_conn.close()
    else:
        print("❌ Failed to connect to database. Please check your database configuration.")
    
    app.run(host="0.0.0.0", port=7500, debug=True)