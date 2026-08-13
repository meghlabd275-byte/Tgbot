#!/usr/bin/env python3
"""
Optional web dashboard for monitoring the Telegram Admin Bot
Run this separately from the main bot for monitoring purposes.
"""

import os
import sys
from datetime import datetime, timedelta
from flask import Flask, render_template_string, jsonify
from database import db
import logging

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# HTML template for the dashboard
DASHBOARD_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Telegram Bot Dashboard</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; }
        .card { background: white; padding: 20px; margin: 10px 0; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; }
        .stat { text-align: center; padding: 15px; background: #007bff; color: white; border-radius: 5px; }
        .stat h3 { margin: 0; font-size: 2em; }
        .stat p { margin: 5px 0 0 0; }
        .table { width: 100%; border-collapse: collapse; margin-top: 10px; }
        .table th, .table td { padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }
        .table th { background: #f8f9fa; }
        .badge { padding: 2px 6px; border-radius: 3px; font-size: 0.8em; }
        .badge-success { background: #28a745; color: white; }
        .badge-danger { background: #dc3545; color: white; }
        .badge-warning { background: #ffc107; color: black; }
        .badge-info { background: #17a2b8; color: white; }
        h1 { color: #333; text-align: center; }
        h2 { color: #666; border-bottom: 2px solid #007bff; padding-bottom: 5px; }
        .refresh { text-align: center; margin: 20px 0; }
        .btn { padding: 8px 16px; background: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer; }
        .btn:hover { background: #0056b3; }
    </style>
    <script>
        function refreshData() {
            location.reload();
        }
        
        // Auto-refresh every 30 seconds
        setInterval(refreshData, 30000);
    </script>
</head>
<body>
    <div class="container">
        <h1>🤖 Telegram Admin Bot Dashboard</h1>
        
        <div class="refresh">
            <button class="btn" onclick="refreshData()">🔄 Refresh</button>
            <small>Last updated: {{ current_time }}</small>
        </div>
        
        <div class="card">
            <h2>📊 Statistics</h2>
            <div class="stats">
                <div class="stat">
                    <h3>{{ stats.total_chats }}</h3>
                    <p>Total Chats</p>
                </div>
                <div class="stat">
                    <h3>{{ stats.active_chats }}</h3>
                    <p>Active Chats</p>
                </div>
                <div class="stat">
                    <h3>{{ stats.total_users }}</h3>
                    <p>Total Users</p>
                </div>
                <div class="stat">
                    <h3>{{ stats.total_admins }}</h3>
                    <p>Bot Admins</p>
                </div>
                <div class="stat">
                    <h3>{{ stats.total_bans }}</h3>
                    <p>Total Bans</p>
                </div>
                <div class="stat">
                    <h3>{{ stats.global_bans }}</h3>
                    <p>Global Bans</p>
                </div>
            </div>
        </div>
        
        <div class="card">
            <h2>💬 Recent Chats</h2>
            <table class="table">
                <thead>
                    <tr>
                        <th>Chat ID</th>
                        <th>Title</th>
                        <th>Status</th>
                        <th>Created</th>
                    </tr>
                </thead>
                <tbody>
                    {% for chat in recent_chats %}
                    <tr>
                        <td><code>{{ chat.id }}</code></td>
                        <td>{{ chat.title or 'N/A' }}</td>
                        <td>
                            {% if chat.is_active %}
                                <span class="badge badge-success">Active</span>
                            {% else %}
                                <span class="badge badge-warning">Inactive</span>
                            {% endif %}
                            {% if chat.is_silenced %}
                                <span class="badge badge-info">Silenced</span>
                            {% endif %}
                            {% if chat.under_attack %}
                                <span class="badge badge-danger">Under Attack</span>
                            {% endif %}
                        </td>
                        <td>{{ chat.created_at.strftime('%Y-%m-%d %H:%M') if chat.created_at else 'N/A' }}</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
        
        <div class="card">
            <h2>🚫 Recent Bans</h2>
            <table class="table">
                <thead>
                    <tr>
                        <th>User ID</th>
                        <th>Chat ID</th>
                        <th>Reason</th>
                        <th>Type</th>
                        <th>Date</th>
                    </tr>
                </thead>
                <tbody>
                    {% for ban in recent_bans %}
                    <tr>
                        <td><code>{{ ban.user_id }}</code></td>
                        <td><code>{{ ban.chat_id }}</code></td>
                        <td>{{ ban.reason or 'No reason' }}</td>
                        <td>
                            {% if ban.is_global %}
                                <span class="badge badge-danger">Global</span>
                            {% else %}
                                <span class="badge badge-warning">Local</span>
                            {% endif %}
                        </td>
                        <td>{{ ban.created_at.strftime('%Y-%m-%d %H:%M') if ban.created_at else 'N/A' }}</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
        
        <div class="card">
            <h2>⚠️ Recent Warnings</h2>
            <table class="table">
                <thead>
                    <tr>
                        <th>User ID</th>
                        <th>Chat ID</th>
                        <th>Reason</th>
                        <th>Type</th>
                        <th>Date</th>
                    </tr>
                </thead>
                <tbody>
                    {% for warning in recent_warnings %}
                    <tr>
                        <td><code>{{ warning.user_id }}</code></td>
                        <td><code>{{ warning.chat_id }}</code></td>
                        <td>{{ warning.reason or 'No reason' }}</td>
                        <td>
                            {% if warning.is_global %}
                                <span class="badge badge-danger">Global</span>
                            {% else %}
                                <span class="badge badge-warning">Local</span>
                            {% endif %}
                        </td>
                        <td>{{ warning.created_at.strftime('%Y-%m-%d %H:%M') if warning.created_at else 'N/A' }}</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
        
        <div class="card">
            <h2>👥 Bot Admins</h2>
            <table class="table">
                <thead>
                    <tr>
                        <th>User ID</th>
                        <th>Chat ID</th>
                        <th>Title</th>
                        <th>Added</th>
                    </tr>
                </thead>
                <tbody>
                    {% for admin in recent_admins %}
                    <tr>
                        <td><code>{{ admin.user_id }}</code></td>
                        <td><code>{{ admin.chat_id }}</code></td>
                        <td>{{ admin.title or 'No title' }}</td>
                        <td>{{ admin.created_at.strftime('%Y-%m-%d %H:%M') if admin.created_at else 'N/A' }}</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
</body>
</html>
"""

@app.route('/')
def dashboard():
    """Main dashboard page"""
    try:
        session = db.get_session()
        
        # Get statistics
        stats = {
            'total_chats': session.query(db.Chat).count(),
            'active_chats': session.query(db.Chat).filter(db.Chat.is_active == True).count(),
            'total_users': session.query(db.User).count(),
            'total_admins': session.query(db.Admin).count(),
            'total_bans': session.query(db.Ban).count(),
            'global_bans': session.query(db.Ban).filter(db.Ban.is_global == True).count(),
        }
        
        # Get recent data
        recent_chats = session.query(db.Chat).order_by(db.Chat.created_at.desc()).limit(10).all()
        recent_bans = session.query(db.Ban).order_by(db.Ban.created_at.desc()).limit(10).all()
        recent_warnings = session.query(db.Warning).order_by(db.Warning.created_at.desc()).limit(10).all()
        recent_admins = session.query(db.Admin).order_by(db.Admin.created_at.desc()).limit(10).all()
        
        session.close()
        
        return render_template_string(
            DASHBOARD_TEMPLATE,
            stats=stats,
            recent_chats=recent_chats,
            recent_bans=recent_bans,
            recent_warnings=recent_warnings,
            recent_admins=recent_admins,
            current_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        )
        
    except Exception as e:
        return f"Error loading dashboard: {e}", 500

@app.route('/api/stats')
def api_stats():
    """API endpoint for statistics"""
    try:
        session = db.get_session()
        
        stats = {
            'total_chats': session.query(db.Chat).count(),
            'active_chats': session.query(db.Chat).filter(db.Chat.is_active == True).count(),
            'total_users': session.query(db.User).count(),
            'total_admins': session.query(db.Admin).count(),
            'total_bans': session.query(db.Ban).count(),
            'global_bans': session.query(db.Ban).filter(db.Ban.is_global == True).count(),
            'total_warnings': session.query(db.Warning).count(),
            'total_mutes': session.query(db.Mute).count(),
            'total_whitelisted': session.query(db.Whitelist).count(),
        }
        
        session.close()
        return jsonify(stats)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/health')
def health_check():
    """Health check endpoint"""
    try:
        session = db.get_session()
        session.execute("SELECT 1")
        session.close()
        
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'database': 'connected'
        })
        
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'timestamp': datetime.now().isoformat(),
            'error': str(e)
        }), 500

if __name__ == '__main__':
    # Check if Flask is installed
    try:
        import flask
    except ImportError:
        print("Flask is not installed. Install it with: pip install flask")
        sys.exit(1)
    
    print("🌐 Starting Telegram Bot Dashboard...")
    print("📊 Dashboard will be available at: http://localhost:5000")
    print("🔗 API endpoints:")
    print("   - Stats: http://localhost:5000/api/stats")
    print("   - Health: http://localhost:5000/api/health")
    print("\n⚠️  Note: This dashboard is for monitoring only.")
    print("   The main bot should be running separately.")
    
    app.run(host='0.0.0.0', port=5000, debug=False)