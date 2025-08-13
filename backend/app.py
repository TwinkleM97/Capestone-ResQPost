import os
import uuid
import boto3
from typing import Optional
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta, timezone
import mimetypes
from flask import abort, send_file
from models import db, Alert

app = Flask(__name__)

# -----------------------------
# App / Upload configuration
# -----------------------------
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    'DATABASE_URL',
    'postgresql://postgres:password@localhost:5432/resqpost'
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Local upload settings
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10 MB
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# CORS
CORS(app)

# DB init
db.init_app(app)

# -----------------------------
# Wasabi (S3-compatible) config
# -----------------------------
WASABI_ACCESS_KEY = os.environ.get('WASABI_ACCESS_KEY')
WASABI_SECRET_KEY = os.environ.get('WASABI_SECRET_KEY')
WASABI_BUCKET = os.environ.get('WASABI_BUCKET', 'resqpost-images')
WASABI_REGION = os.environ.get('WASABI_REGION', 'us-east-1')

s3_client = None
if WASABI_ACCESS_KEY and WASABI_SECRET_KEY:
    try:
        s3_client = boto3.client(
            's3',
            endpoint_url='https://s3.wasabisys.com',
            aws_access_key_id=WASABI_ACCESS_KEY,
            aws_secret_access_key=WASABI_SECRET_KEY,
            region_name=WASABI_REGION
        )
    except Exception as e:
        print(f"[WARN] Failed to init Wasabi client: {e}")
        s3_client = None


# -----------------------------
# Helpers
# -----------------------------
def _normalize_image_url(url: Optional[str]) -> Optional[str]:
    """
    Ensure local paths are absolute (start with '/').
    Leave external http(s) URLs untouched.
    """
    if not url:
        return url
    if url.startswith('http://') or url.startswith('https://'):
        return url
    # handle legacy rows saved as 'uploads/..'
    return url if url.startswith('/') else f'/{url}'


def _save_local(file_storage) -> str:
    """Save file locally and return public URL path (always /uploads/...)."""
    fn = secure_filename(file_storage.filename or 'upload')
    unique = f"{uuid.uuid4()}_{fn}"
    path = os.path.join(app.config['UPLOAD_FOLDER'], unique)
    file_storage.save(path)
    # always return absolute app-relative URL
    return f"/uploads/{unique}"


def upload_image(file_storage) -> Optional[str]:
    """
    Upload to Wasabi if configured; otherwise save locally.
    Return a URL (absolute or app-relative) that the frontend can use.
    """
    if not file_storage or not file_storage.filename:
        return None

    # Try Wasabi first
    if s3_client:
        try:
            fn = secure_filename(file_storage.filename or 'upload')
            key = f"{uuid.uuid4()}_{fn}"
            s3_client.upload_fileobj(
                file_storage,
                WASABI_BUCKET,
                key,
                ExtraArgs={'ACL': 'public-read'}
            )
            return f"https://s3.wasabisys.com/{WASABI_BUCKET}/{key}"
        except Exception as e:
            print(f"[WARN] Wasabi upload failed, using local: {e}")

    # Fallback to local
    return _save_local(file_storage)


# -----------------------------
# API routes
# -----------------------------
@app.route('/api/alerts', methods=['GET'])
def get_alerts():
    """Get all alerts with optional filtering."""
    try:
        query = Alert.query

        # Filter by category
        category = request.args.get('category')
        if category in ('person', 'pet'):
            query = query.filter(Alert.category == category)

        # Filter by location (basic text search)
        location = request.args.get('location')
        if location:
            query = query.filter(Alert.location.ilike(f'%{location}%'))

        # Filter by resolved status
        resolved = request.args.get('resolved')
        if resolved is not None:
            query = query.filter(Alert.is_resolved == (resolved.lower() == 'true'))

        # Restrict to last N days (default 30) using timezone-aware UTC
        days = request.args.get('days', 30)
        try:
            days = int(days)
            cutoff = datetime.now(timezone.utc) - timedelta(days=days)
            query = query.filter(Alert.created_at >= cutoff)
        except Exception:
            pass

        alerts = query.order_by(Alert.created_at.desc()).all()

        payload = []
        for a in alerts:
            d = a.to_dict()
            d['image_url'] = _normalize_image_url(d.get('image_url'))
            payload.append(d)

        return jsonify({'success': True, 'alerts': payload, 'count': len(payload)})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/alerts', methods=['POST'])
def create_alert():
    """Create a new alert."""
    try:
        data = request.form.to_dict()

        # Validate required fields
        for field in ('title', 'description', 'category', 'location'):
            if not data.get(field):
                return jsonify({'success': False, 'error': f'{field} is required'}), 400

        # Image (Wasabi or local)
        image_url = None
        if 'image' in request.files:
            image_url = upload_image(request.files['image'])
        # Defensive: normalize again (covers any legacy or edge cases)
        image_url = _normalize_image_url(image_url)

        # Create new alert
        alert = Alert(
            title=data['title'],
            description=data['description'],
            category=data['category'],
            location=data['location'],
            latitude=float(data['latitude']) if data.get('latitude') else None,
            longitude=float(data['longitude']) if data.get('longitude') else None,
            image_url=image_url,
            contact_name=data.get('contact_name'),
            contact_phone=data.get('contact_phone'),
            contact_email=data.get('contact_email')
        )

        db.session.add(alert)
        db.session.commit()

        d = alert.to_dict()
        d['image_url'] = _normalize_image_url(d.get('image_url'))

        return jsonify({'success': True, 'alert': d, 'message': 'Alert created successfully'}), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/alerts/<alert_id>', methods=['GET'])
def get_alert(alert_id):
    """Get a specific alert by ID."""
    try:
        alert = Alert.query.get_or_404(alert_id)
        d = alert.to_dict()
        d['image_url'] = _normalize_image_url(d.get('image_url'))
        return jsonify({'success': True, 'alert': d})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/alerts/<alert_id>/resolve', methods=['PATCH'])
def resolve_alert(alert_id):
    """Mark an alert as resolved."""
    try:
        alert = Alert.query.get_or_404(alert_id)
        alert.is_resolved = True
        alert.updated_at = datetime.now(timezone.utc)

        db.session.commit()

        d = alert.to_dict()
        d['image_url'] = _normalize_image_url(d.get('image_url'))

        return jsonify({'success': True, 'alert': d, 'message': 'Alert marked as resolved'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/alerts/nearby', methods=['GET'])
def get_nearby_alerts():
    """Get alerts near a specific location (very rough distance)."""
    try:
        lat = request.args.get('latitude', type=float)
        lon = request.args.get('longitude', type=float)
        radius = request.args.get('radius', 10, type=float)  # km

        if lat is None or lon is None:
            return jsonify({'success': False, 'error': 'Latitude and longitude are required'}), 400

        alerts = Alert.query.filter(
            Alert.latitude.isnot(None),
            Alert.longitude.isnot(None),
            Alert.is_resolved == False
        ).all()

        # naive distance (not great, but fine for now)
        nearby = []
        for a in alerts:
            lat_diff = abs(a.latitude - lat)
            lon_diff = abs(a.longitude - lon)
            distance = ((lat_diff ** 2) + (lon_diff ** 2)) ** 0.5 * 111  # km
            if distance <= radius:
                d = a.to_dict()
                d['image_url'] = _normalize_image_url(d.get('image_url'))
                d['distance'] = round(distance, 2)
                nearby.append(d)

        return jsonify({'success': True, 'alerts': nearby, 'count': len(nearby)})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    ts = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    return jsonify({'status': 'healthy', 'timestamp': ts, 'version': '1.0.0'})


# Serve local uploads (cache for a year; safe for immutable filenames)
# Serve local uploads (cache for a year; safe for immutable filenames)
@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    safe = os.path.normpath(filename).lstrip(os.sep)
    full_path = os.path.join(app.config['UPLOAD_FOLDER'], safe)

    if not os.path.isfile(full_path):
        app.logger.warning("Upload not found: %s", full_path)
        abort(404)

    resp = send_file(full_path, conditional=True)
    resp.headers["Cache-Control"] = "public, max-age=31536000, immutable"
    return resp

# Some Python builds don’t know these yet
mimetypes.add_type('image/avif', '.avif', strict=False)
mimetypes.add_type('image/webp', '.webp', strict=False)

# -----------------------------
# Boot
# -----------------------------
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    # Flask dev server
    app.run(debug=True, host='0.0.0.0', port=5000)
