from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv
import os
import asyncio
from datetime import datetime
from services import leads
from services.data_collector import DataCollector
from asgiref.wsgi import WsgiToAsgi
from functools import wraps

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__, 
          template_folder=os.path.join(os.path.dirname(__file__), 'templates'),
          static_folder=os.path.join(os.path.dirname(__file__), 'static'))

app.config['JSON_SORT_KEYS'] = False  # Preserve JSON key order

# Configure CORS to allow all origins
CORS(app, resources={r"/*": {"origins": "*"}})

# Convert to ASGI app for async support
asgi_app = WsgiToAsgi(app)

# Helper for async routes
def async_route(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        return asyncio.run(f(*args, **kwargs))
    return wrapper

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/scan')
@async_route
async def scan_opportunities():
    try:
        collector = DataCollector()
        opportunities = await collector.scan_opportunities()
        return jsonify({
            'status': 'success',
            'data': opportunities,
            'count': len(opportunities)
        })
    except Exception as e:
        app.logger.error(f"Error in scan_opportunities: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/leads')
@async_route
async def get_leads():
    # Get query parameters
    page = request.args.get('page', default=1, type=int)
    limit = request.args.get('limit', default=10, type=int)
    sort_field = request.args.get('sortField', default='dateAdded', type=str)
    sort_direction = request.args.get('sortDirection', default='desc', type=str)
    
    try:
        # Get leads from service
        result = await leads.get_leads()
        return jsonify(result)
    except Exception as e:
        app.logger.error(f"Error getting leads: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(asgi_app, host='127.0.0.1', port=5001, debug=True)
