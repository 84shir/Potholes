import os, glob, datetime, mimetypes
from werkzeug.utils import secure_filename
from flask import Blueprint, request, jsonify, current_app, abort, send_file
from services.s3_service import S3Service
from services.filter import filter_potholes
import kaggle_to_tigris
from collections import Counter
import random



bp = Blueprint('api', __name__, url_prefix = '/api')
@bp.route('/potholes', methods=['GET'])
def get_potholes():
    s3: S3Service = current_app.s3
    data = current_app.pothole_data
    results = filter_potholes(request.args, data)

    for p in results:
        # your bucket has: <date-folder>/<base>.json  &  <base>_best.<ext>
        if p.get('s3_prefix') and p.get('s3_base'):
            prefix = f"{p['s3_prefix']}/{p['s3_base']}_best"
            try:
                # List objects in the bucket to find matching image files
                p['image_url'] = current_app.s3.presign_image_get(prefix)
            except Exception as e:
                current_app.logger.warning(f"Couldn't find or presign image for {prefix}: {e}")
                p['image_url'] = None
    return jsonify(results)

@bp.route('/delete_today_directory', methods=['DELETE'])
def delete_today_directory():
    """
    Delete all objects under today's date in S3, and return the list of deleted keys.
    """
    today_prefix = datetime.date.today().isoformat()
    deleted = current_app.delete_s3_directory(today_prefix)
    if not deleted:
        return jsonify({'message': f'No objects found under "{today_prefix}/"'}), 404
    return jsonify({'deleted': deleted}), 200


@bp.route('/generate_presigned_url', methods=['POST'])
def generate_presigned_url():
    s3: S3Service = current_app.s3
    payload = request.get_json(force=True)
    

    # Single-file upload
    if not payload.get('dataset_url'):
        file_name = payload.get('file_name')
        file_type = payload.get('file_type')
        if not file_name or not file_type:
            abort(400, "file_name and file_type are required")
        try:
            presigned_post = s3.generate_presigned_post(
                Key=file_name,
                content_type = file_type
            )
            return jsonify({'data': presigned_post})
        except Exception as e:
            current_app.logger.error("Failed to presign single upload")
            return jsonify({'error': str(e)}), 500

    # Kaggle dataset bulk upload
    dataset_url = payload['dataset_url']
    kaggle_api = kaggle_to_tigris.kaggle_auth()
    dataset = kaggle_to_tigris.pull_images_from_dataset(kaggle_api, dataset_url)
    files = glob.glob(f"{dataset}/**/*.*", recursive=True)

    presigned_urls = []
    for file_path in files:
        file_name = secure_filename(os.path.basename(file_path))
        content_type = mimetypes.guess_type(file_name)[0] or 'application/octet-stream'
        try:

            presigned_post = s3.generate_presigned_post(
                Key=f"{dataset}/{file_name}",
                content_type = content_type
            )
            presigned_urls.append({
                "file_name": file_name,
                "file_path": file_path,
                "url": presigned_post['url'],
                "fields": presigned_post['fields']
            })
        except Exception:
            current_app.logger.warning(f"Skipping presign for {name}")
    return jsonify({'results': presigned_urls})

@bp.route('/list_buckets', methods=['GET'])
def list_buckets():
    s3: S3Service = current_app.s3
    try:
        buckets = s3.svc.list_buckets().get('Buckets', [])
        result = {}
        for b in buckets:
            name = b['Name']
            objs = s3.svc.list_objects_v2(Bucket=name).get('Contents', [])
            result[name] = [o['Key'] for o in objs]
        return jsonify({'buckets': result})
    except Exception as e:
        app.logger.error(f"Error listing buckets: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/analytics/summary', methods=['GET'])
def analytics_summary():
    """Generate analytics summary from real S3 data"""
    try:
        data = current_app.pothole_data

        if not data:
            return jsonify({
                'metrics': {
                    'total': 0,
                    'highSeverity': 0,
                    'weekly': 0,
                    'confidence': 0,
                    'totalChange': 0,
                    'severityChange': 0,
                    'weeklyTrend': 0
                },
                'charts': {
                    'trends': {'labels': [], 'data': []},
                    'severity': [0, 0, 0, 0],
                    'geographic': {'labels': [], 'data': []},
                    'timeDistribution': [0, 0, 0, 0]
                },
                'recent': []
            })

        # Calculate metrics from real data
        total_count = len(data)
        high_severity_count = len([p for p in data if p.get('severity', 0) >= 4])

        # Calculate weekly detections (last 7 days)
        week_ago = datetime.datetime.now() - datetime.timedelta(days=7)
        weekly_count = len([p for p in data if datetime.datetime.fromisoformat(p.get('date', '1970-01-01')) >= week_ago])

        # Calculate average confidence
        confidences = [p.get('confidence', 0) for p in data if p.get('confidence')]
        avg_confidence = round(sum(confidences) / len(confidences) if confidences else 0, 1)

        # Generate trends data (last 30 days)
        trends_data = generate_trends_from_data(data)

        # Severity distribution
        severity_counts = Counter(p.get('severity', 1) for p in data)
        severity_distribution = [
            severity_counts.get(1, 0),  # Low
            severity_counts.get(2, 0),  # Medium
            severity_counts.get(3, 0),  # High
            severity_counts.get(4, 0) + severity_counts.get(5, 0)  # Critical
        ]

        # Geographic distribution (simplified by coordinate ranges)
        geo_data = generate_geographic_distribution(data)

        # Time distribution (by hour of day)
        time_dist = generate_time_distribution(data)

        # Recent activity (last 10 items)
        recent_activity = generate_recent_activity(data)

        return jsonify({
            'metrics': {
                'total': total_count,
                'highSeverity': high_severity_count,
                'weekly': weekly_count,
                'confidence': avg_confidence,
                'totalChange': calculate_change_percentage(data, 'total'),
                'severityChange': calculate_change_percentage(data, 'severity'),
                'weeklyTrend': round(weekly_count / 7, 1)
            },
            'charts': {
                'trends': trends_data,
                'severity': severity_distribution,
                'geographic': geo_data,
                'timeDistribution': time_dist
            },
            'recent': recent_activity
        })

    except Exception as e:
        current_app.logger.error(f"Error generating analytics: {e}")
        return jsonify({'error': 'Failed to generate analytics'}), 500

@bp.route('/incidents/stats', methods=['GET'])
def incidents_stats():
    """Generate incident statistics from S3 data"""
    try:
        data = current_app.pothole_data

        if not data:
            return jsonify({
                'active': 0,
                'pending': 0,
                'inProgress': 0,
                'resolved': 0
            })

        # For now, simulate incident statuses since we don't have status field in data
        # In a real implementation, you'd have a status field or separate incidents table
        total = len(data)

        # Distribute incidents across statuses based on severity and date
        recent_count = len([p for p in data if is_recent(p.get('date'), days=7)])
        high_severity_count = len([p for p in data if p.get('severity', 0) >= 4])

        stats = {
            'active': high_severity_count,  # High severity items are "active"
            'pending': recent_count - high_severity_count if recent_count > high_severity_count else 0,
            'inProgress': min(5, total // 4),  # Simulate some in progress
            'resolved': max(0, total - high_severity_count - (recent_count - high_severity_count) - min(5, total // 4))
        }

        return jsonify(stats)

    except Exception as e:
        current_app.logger.error(f"Error generating incident stats: {e}")
        return jsonify({'error': 'Failed to generate incident stats'}), 500

def generate_trends_from_data(data):
    """Generate trend data from actual pothole dates"""
    if not data:
        return {'labels': [], 'data': []}

    # Group by date
    date_counts = Counter()
    for p in data:
        date_str = p.get('date', '')
        if date_str:
            try:
                date = datetime.datetime.fromisoformat(date_str).date()
                date_counts[date.isoformat()] += 1
            except:
                continue

    # Get last 30 days
    today = datetime.date.today()
    labels = []
    data_points = []

    for i in range(29, -1, -1):
        date = today - datetime.timedelta(days=i)
        labels.append(date.strftime('%m/%d'))
        data_points.append(date_counts.get(date.isoformat(), 0))

    return {'labels': labels, 'data': data_points}

def generate_geographic_distribution(data):
    """Generate geographic distribution from coordinates"""
    if not data:
        return {'labels': [], 'data': []}

    # Simple geographic bucketing by coordinate ranges
    regions = {
        'North': 0,
        'South': 0,
        'East': 0,
        'West': 0,
        'Central': 0
    }

    # Calculate center point
    lats = [p.get('lat', 0) for p in data if p.get('lat')]
    lngs = [p.get('lng', 0) for p in data if p.get('lng')]

    if lats and lngs:
        center_lat = sum(lats) / len(lats)
        center_lng = sum(lngs) / len(lngs)

        for p in data:
            lat = p.get('lat', 0)
            lng = p.get('lng', 0)

            if lat and lng:
                if lat > center_lat + 0.01:
                    regions['North'] += 1
                elif lat < center_lat - 0.01:
                    regions['South'] += 1
                elif lng > center_lng + 0.01:
                    regions['East'] += 1
                elif lng < center_lng - 0.01:
                    regions['West'] += 1
                else:
                    regions['Central'] += 1

    return {
        'labels': list(regions.keys()),
        'data': list(regions.values())
    }

def generate_time_distribution(data):
    """Generate time of day distribution"""
    if not data:
        return [0, 0, 0, 0]

    time_periods = [0, 0, 0, 0]  # Morning, Afternoon, Evening, Night

    for p in data:
        # Use timestamp or date to determine time period
        # For now, distribute based on ID or random since we might not have time info
        timestamp = p.get('id', 0)
        if timestamp:
            hour = (timestamp % 24) if isinstance(timestamp, int) else hash(str(timestamp)) % 24

            if 6 <= hour < 12:
                time_periods[0] += 1  # Morning
            elif 12 <= hour < 18:
                time_periods[1] += 1  # Afternoon
            elif 18 <= hour < 24:
                time_periods[2] += 1  # Evening
            else:
                time_periods[3] += 1  # Night

    return time_periods

def generate_recent_activity(data):
    """Generate recent activity from data"""
    if not data:
        return []

    # Sort by date/ID and take last 10
    sorted_data = sorted(data, key=lambda x: x.get('date', ''), reverse=True)[:10]

    activity = []
    for p in sorted_data:
        activity.append({
            'timestamp': p.get('date', datetime.datetime.now().isoformat()),
            'location': f"{p.get('lat', 0):.4f}, {p.get('lng', 0):.4f}",
            'severity': p.get('severity', 1),
            'confidence': p.get('confidence', 95),
            'status': 'new' if is_recent(p.get('date'), days=1) else 'processed'
        })

    return activity

def calculate_change_percentage(data, metric_type):
    """Calculate percentage change from previous period"""
    if not data or len(data) < 2:
        return 0

    # Simple calculation based on data distribution
    if metric_type == 'total':
        # Compare recent week vs previous week
        now = datetime.datetime.now()
        week_ago = now - datetime.timedelta(days=7)
        two_weeks_ago = now - datetime.timedelta(days=14)

        recent_week = len([p for p in data if is_between_dates(p.get('date'), week_ago, now)])
        prev_week = len([p for p in data if is_between_dates(p.get('date'), two_weeks_ago, week_ago)])

        if prev_week == 0:
            return 100 if recent_week > 0 else 0

        return round(((recent_week - prev_week) / prev_week) * 100, 1)

    return 0

def is_recent(date_str, days=7):
    """Check if date is within recent days"""
    if not date_str:
        return False

    try:
        date = datetime.datetime.fromisoformat(date_str)
        cutoff = datetime.datetime.now() - datetime.timedelta(days=days)
        return date >= cutoff
    except:
        return False

def is_between_dates(date_str, start_date, end_date):
    """Check if date is between two dates"""
    if not date_str:
        return False

    try:
        date = datetime.datetime.fromisoformat(date_str)
        return start_date <= date <= end_date
    except:
        return False

@bp.route('/incidents', methods=['POST'])
def create_incident():
    """Create a new incident report and store in S3"""
    try:
        data = request.get_json()

        # Validate required fields
        required_fields = ['lat', 'lng', 'severity', 'description']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400

        # Generate incident data
        timestamp = int(datetime.datetime.now().timestamp())
        date_folder = datetime.date.today().isoformat()

        incident_data = {
            "timestamp": timestamp,
            "gps": {
                "lat": float(data['lat']),
                "lon": float(data['lng'])
            },
            "description": data['description'],
            "severity": int(data['severity']),
            "confidence": float(data.get('confidence', 95)) / 100,
            "reported_by": "web_interface",
            "status": "pending"
        }

        # Store in S3
        s3_key = f"{date_folder}/incident_{timestamp}.json"
        s3: S3Service = current_app.s3

        import json
        s3.svc.put_object(
            Bucket=s3.bucket,
            Key=s3_key,
            Body=json.dumps(incident_data),
            ContentType='application/json'
        )

        # Reload pothole data to include new incident
        current_app.pothole_data = current_app.s3.fetch_pothole_data()

        return jsonify({
            'success': True,
            'incident_id': timestamp,
            's3_key': s3_key
        }), 201

    except Exception as e:
        current_app.logger.error(f"Error creating incident: {e}")
        return jsonify({'error': 'Failed to create incident'}), 500

@bp.route('/incidents/<incident_id>', methods=['GET'])
def get_incident_details(incident_id):
    """Get detailed information about a specific incident from S3"""
    try:
        data = current_app.pothole_data

        # Find incident by ID
        incident = None
        for p in data:
            if str(p.get('id')) == str(incident_id):
                incident = p
                break

        if not incident:
            return jsonify({'error': 'Incident not found'}), 404

        # Add additional details
        incident_details = {
            **incident,
            'status': getIncidentStatus(incident),
            'days_since_detection': getDaysSince(incident.get('date')),
            'coordinates_formatted': f"{incident.get('lat', 0):.6f}, {incident.get('lng', 0):.6f}",
            'severity_text': getSeverityText(incident.get('severity', 1)),
            'confidence_percent': round((incident.get('confidence', 0)) * 100)
        }

        return jsonify(incident_details)

    except Exception as e:
        current_app.logger.error(f"Error fetching incident details: {e}")
        return jsonify({'error': 'Failed to fetch incident details'}), 500

def getSeverityText(severity):
    severity_map = {
        1: 'Low',
        2: 'Medium',
        3: 'High',
        4: 'Critical',
        5: 'Emergency'
    }
    return severity_map.get(severity, 'Unknown')

def getIncidentStatus(incident):
    """Determine incident status based on S3 data"""
    if not incident:
        return 'unknown'

    days_since = getDaysSince(incident.get('date'))
    severity = incident.get('severity', 1)

    if severity >= 4:
        return 'active'  # High severity = active
    elif days_since <= 1:
        return 'pending'  # Recent = pending review
    elif days_since <= 7 and severity >= 3:
        return 'in_progress'  # Medium severity within week = in progress
    else:
        return 'resolved'  # Older or low severity = resolved

def getDaysSince(date_string):
    """Calculate days since a given date"""
    try:
        date = datetime.datetime.fromisoformat(date_string)
        now = datetime.datetime.now()
        return (now - date).days
    except:
        return 999


