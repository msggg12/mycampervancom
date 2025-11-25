from flask import Flask, jsonify, send_from_directory, request, make_response, redirect
import json
import os
import requests
from icalendar import Calendar
from datetime import datetime
from dateutil import tz
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import re

# Try to import email validator, fall back to simple regex if not available
try:
	from email_validator import validate_email, EmailNotValidError
	EMAIL_VALIDATOR_AVAILABLE = True
except ImportError:
	EMAIL_VALIDATOR_AVAILABLE = False
	def validate_email(email):
		# Simple email regex fallback
		pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
		if not re.match(pattern, email):
			raise ValueError("Invalid email format")
		return email
	class EmailNotValidError(Exception):
		pass

app = Flask(__name__, static_folder="static", template_folder="static")

try:
	import stripe
except Exception:
	stripe = None


STORE_PATH = os.path.join(os.path.dirname(__file__), 'messages.json')
STATS_PATH = os.path.join(os.path.dirname(__file__), 'stats.json')


def load_config():
	config_path = os.path.join(os.path.dirname(__file__), "config.json")
	if not os.path.exists(config_path):
		return {"vans": [], "contact": {}, "email": {}, "stripe": {} }
	with open(config_path, "r", encoding="utf-8") as f:
		return json.load(f)


def save_config(cfg):
	config_path = os.path.join(os.path.dirname(__file__), "config.json")
	with open(config_path, "w", encoding="utf-8") as f:
		json.dump(cfg, f, ensure_ascii=False, indent=2)


def is_admin(req):
	return req.cookies.get('admin_auth') == '1'


def load_messages():
	# Load stored messages (bookings and contact messages)
	# This function returns a list and does not perform admin checks (caller should enforce authorization).
	if not os.path.exists(STORE_PATH):
		return []
	try:
		with open(STORE_PATH, 'r', encoding='utf-8') as f:
			return json.load(f)
	except Exception:
		return []



def save_message(msg):
	msgs = load_messages()

	msgs.append(msg)
	with open(STORE_PATH, 'w', encoding='utf-8') as f:
		json.dump(msgs, f, ensure_ascii=False, indent=2)


def save_messages(msgs):
	with open(STORE_PATH, 'w', encoding='utf-8') as f:
		json.dump(msgs, f, ensure_ascii=False, indent=2)


def load_stats():
	if not os.path.exists(STATS_PATH):
		return { 'total': 0, 'pages': {}, 'ips': {}, 'log': [] }
	try:
		with open(STATS_PATH, 'r', encoding='utf-8') as f:
			data = json.load(f)
			data.setdefault('ips', {})
			data.setdefault('log', [])
			return data
	except Exception:
		return { 'total': 0, 'pages': {}, 'ips': {}, 'log': [] }



def save_stats(stats):

	with open(STATS_PATH, 'w', encoding='utf-8') as f:
		json.dump(stats, f, ensure_ascii=False, indent=2)


def send_email(subject: str, body: str, from_email: str = None, to_email: str = None) -> bool:
	cfg = load_config().get("email", {})
	host = cfg.get("smtpHost")
	port = int(cfg.get("smtpPort" or 0))
	user = cfg.get("smtpUser")
	pwd = cfg.get("smtpPass")
	to_addr = to_email or cfg.get("toEmail", "jonibuliskeria@gmail.com")  # Use provided to_email or default to admin
	from_addr = from_email or user
	
	if not (host and port and to_addr and from_addr):
		print(f"Email not sent: missing smtp config (host={host}, port={port}, to={to_addr}, from={from_addr})")
		return False
	try:
		print(f"Sending email to {to_addr} via {host}:{port} from {from_addr}")
		# Validate email addresses
		validate_email(to_addr)
		if from_email:
			validate_email(from_email)
		
		msg = MIMEMultipart()
		msg["Subject"] = subject
		msg["From"] = from_addr
		msg["To"] = to_addr
		
		# Add body as both plain text and HTML
		msg.attach(MIMEText(body, "plain", "utf-8"))
		
		with smtplib.SMTP(host, port, timeout=15) as smtp:
			smtp.starttls()
			if user and pwd:
				smtp.login(user, pwd)
			smtp.sendmail(from_addr, [to_addr], msg.as_string())
		return True
	except (EmailNotValidError, Exception) as e:
		print(f"Email error: {e}")
		return False


@app.route('/api/test-email', methods=['POST'])
def api_test_email():
	if not is_admin(request):
		return jsonify({"error": "unauthorized"}), 401
	data = request.get_json(force=True) or {}
	subject = data.get('subject') or 'Test email from MyCamperVans'
	body = data.get('body') or 'This is a test email sent from your site to confirm SMTP is working.'
	to = data.get('to') or load_config().get('email', {}).get('toEmail') or 'jonibuliskeria@gmail.com'
	ok = send_email(subject, body, None, to_email=to)
	return jsonify({ 'ok': bool(ok) })


@app.route("/")
def index():
	return send_from_directory(app.static_folder, "index.html")


@app.route("/vans")
def vans_page():
	return send_from_directory(app.static_folder, "vans.html")


@app.route("/van/<slug>")
def van_page(slug):
	return send_from_directory(app.static_folder, "van.html")


@app.route("/contact")
def contact_page():
	return send_from_directory(app.static_folder, "contact.html")


@app.route("/about")
def about_page():
	return send_from_directory(app.static_folder, "about.html")


@app.route("/locations")
def locations_page():
	return redirect("https://www.airbnb.co.uk/s/guidebooks?refinement_paths%5B%5D=/guidebooks/2908833", code=302)


@app.route("/admin")
def admin_page():
	if not is_admin(request):
		return send_from_directory(app.static_folder, "admin_login.html")
	return send_from_directory(app.static_folder, "admin.html")


@app.route('/api/admin-login', methods=['POST'])
def admin_login():
	data = request.get_json(force=True)
	username = (data.get('username') or '').strip()
	password = (data.get('password') or '').strip()
	if username == 'admin' and password == 'joni8252':
		resp = make_response(jsonify({ 'ok': True }))
		resp.set_cookie('admin_auth','1', httponly=True, samesite='Lax')
		return resp
	return jsonify({ 'ok': False, 'error': 'Invalid credentials' }), 401


@app.route('/api/admin-logout', methods=['POST'])
def admin_logout():
	resp = make_response(jsonify({ 'ok': True }))
	resp.set_cookie('admin_auth','', expires=0)
	return resp


@app.route("/api/site")
def site_info():
	cfg = load_config()
	return jsonify({ "contact": cfg.get("contact", {} ), "stripe": {"publicKey": (cfg.get("stripe", {}).get("publicKey") or "") } })


@app.route("/api/site-content")
def site_content():
	cfg = load_config()
	return jsonify(cfg.get("site_content", {}))


@app.route('/api/admin/update-site-content', methods=['POST'])
def update_site_content():
	if not is_admin(request):
		return jsonify({"error":"unauthorized"}), 401
	
	try:
		data = request.get_json(force=True)
		updates = data.get('updates', {})
		
		if not updates:
			return jsonify({"error": "No updates provided"}), 400
		
		config = load_config()
		
		# Update the site_content section
		if 'site_content' not in config:
			config['site_content'] = {}
		
		# Deep merge the updates
		for key, value in updates.items():
			if isinstance(value, dict) and isinstance(config['site_content'].get(key), dict):
				# Merge nested dictionaries
				config['site_content'][key].update(value)
			else:
				config['site_content'][key] = value
		
		# Save updated config
		save_config(config)
		
		return jsonify({"ok": True, "message": "Site content updated successfully"})
	except Exception as e:
		return jsonify({"error": str(e)}), 500


@app.route("/api/vans")
def vans():
	config = load_config()
	vans_out = []
	for v in (config.get("vans", []) or []):
		vv = dict(v)
		if not vv.get('airbnbUrl'):
			ical = vv.get('airbnbIcalUrl') or ''
			import re
			m = re.search(r"/ical/(\d+)", ical)
			if m:
				vv['airbnbUrl'] = f"https://www.airbnb.com/rooms/{m.group(1)}"
		vans_out.append(vv)
	return jsonify(vans_out)


@app.route("/api/messages")
def api_messages():
	if not is_admin(request):
		return jsonify({"error":"unauthorized"}), 401
	return jsonify(load_messages())


@app.route('/api/track', methods=['POST'])
def track():
	stats = load_stats()
	try:
		p = request.get_json(force=True)
		path = (p.get('path') or '/').split('?')[0]
		ip = request.headers.get('X-Forwarded-For', '').split(',')[0].strip() or request.remote_addr or 'unknown'
		ua = request.headers.get('User-Agent', '')
		
		# increment totals
		stats['total'] = int(stats.get('total',0)) + 1
		pages = stats.get('pages') or {}
		pages[path] = int(pages.get(path,0)) + 1
		stats['pages'] = pages
		
		# per-ip stats
		ips = stats.get('ips') or {}
		# attempt to resolve country for this IP (use a lightweight public API). Keep this optional/fail-safe.
		country = 'Unknown'
		try:
			if ip and ip not in ('', 'unknown', '127.0.0.1', '::1'):
				# ipapi.co returns JSON with country_name and country
				resp = requests.get(f"https://ipapi.co/{ip}/json/", timeout=3)
				if resp.ok:
					j = resp.json()
					# store the raw lookup in the running stats object so it isn't lost
					try:
						gd = stats.get('geo_debug') or {}
						gd[ip] = { 'ok': True, 'data': j }
						stats['geo_debug'] = gd
					except Exception:
						pass
					country = j.get('country_name') or j.get('country') or 'Unknown'
				else:
					# record non-200 response for debugging
					try:
						gd = stats.get('geo_debug') or {}
						gd[ip] = { 'ok': False, 'status_code': resp.status_code, 'text': resp.text[:500] }
						stats['geo_debug'] = gd
					except Exception:
						pass
					country = 'Unknown'
			else:
				country = 'Local'
		except Exception as exc:
			# network or parse error — store exception for debugging and fallback to Unknown
			try:
				gd = stats.get('geo_debug') or {}
				gd[ip] = { 'ok': False, 'error': str(exc) }
				stats['geo_debug'] = gd
			except Exception:
				pass
			country = 'Unknown'
		
		info = ips.get(ip) or { 'count': 0, 'pages': {}, 'last': None, 'ua': ua }
		info['count'] = int(info.get('count',0)) + 1
		pp = info.get('pages') or {}
		pp[path] = int(pp.get(path,0)) + 1
		info['pages'] = pp
		info['last'] = datetime.utcnow().isoformat() + 'Z'
		info['ua'] = ua or info.get('ua','')
		# Ensure country is stored/updated for this IP (force set so it's included in saved stats)
		info['country'] = country
		ips[ip] = info
		stats['ips'] = ips
		
		# aggregate visits by country (counts visits, not unique IPs)
		by_country = stats.get('by_country_visits') or {}
		ct = country or info.get('country') or 'Unknown'
		by_country[ct] = int(by_country.get(ct, 0)) + 1
		stats['by_country_visits'] = by_country
		
		# append to rolling log
		log = stats.get('log') or []
		log.append({ 'ts': datetime.utcnow().isoformat() + 'Z', 'ip': ip, 'path': path, 'ua': ua })
		# keep only last 500
		stats['log'] = log[-500:]
		
		save_stats(stats)
		return jsonify({'ok': True})
	except Exception as e:
		print(f"Track error: {e}")
		return jsonify({'ok': False, 'error': str(e)}), 400


@app.route('/api/stats')
def stats():
	if not is_admin(request):
		return jsonify({"error":"unauthorized"}), 401
	stats_data = load_stats()
	# Ensure we have some default data if empty
	if not stats_data.get('total'):
		stats_data['total'] = 0
	if not stats_data.get('pages'):
		stats_data['pages'] = {}
	if not stats_data.get('ips'):
		stats_data['ips'] = {}
	if not stats_data.get('log'):
		stats_data['log'] = []
	if not stats_data.get('confirmed_revenue'):
		stats_data['confirmed_revenue'] = 0
	
	# Calculate unique visitors (unique IPs)
	unique_ips = len(stats_data.get('ips', {}))
	stats_data['unique_visitors'] = unique_ips

	# Aggregate by country: total visits and unique IPs per country
	by_country_visits = stats_data.get('by_country_visits') or {}
	# compute unique IPs per country from stats_data['ips']
	by_country_unique = {}
	for ip, info in (stats_data.get('ips') or {}).items():
		c = info.get('country') or 'Unknown'
		by_country_unique[c] = int(by_country_unique.get(c, 0)) + 1

	stats_data['by_country_visits'] = by_country_visits
	stats_data['by_country_unique'] = by_country_unique
	
	return jsonify(stats_data)

@app.route('/api/test-stats', methods=['POST'])
def test_stats():
	if not is_admin(request):
		return jsonify({"error":"unauthorized"}), 401
	# Generate some test statistics
	stats = load_stats()
	stats['total'] = stats.get('total', 0) + 1
	stats['pages'] = stats.get('pages', {})
	stats['pages']['/'] = stats['pages'].get('/', 0) + 1
	stats['pages']['/vans'] = stats['pages'].get('/vans', 0) + 1
	stats['ips'] = stats.get('ips', {})
	stats['ips']['127.0.0.1'] = {
		'count': stats['ips'].get('127.0.0.1', {}).get('count', 0) + 1,
		'pages': {'/': 1, '/vans': 1},
		'last': datetime.utcnow().isoformat() + 'Z',
		'ua': 'Test Browser'
	}
	stats['log'] = stats.get('log', [])
	stats['log'].append({
		'ts': datetime.utcnow().isoformat() + 'Z',
		'ip': '127.0.0.1',
		'path': '/',
		'ua': 'Test Browser'
	})
	save_stats(stats)
	return jsonify({'ok': True, 'message': 'Test stats added'})

@app.route('/api/admin/upload-image', methods=['POST'])
def upload_image():
	if not is_admin(request):
		return jsonify({"error":"unauthorized"}), 401
	
	if 'file' not in request.files:
		return jsonify({"error": "No file provided"}), 400
	
	file = request.files['file']
	van_slug = request.form.get('van_slug')
	
	if file.filename == '':
		return jsonify({"error": "No file selected"}), 400
	
	if not van_slug:
		return jsonify({"error": "Van slug required"}), 400
	
	# Create van-specific directory
	van_dir = os.path.join('static', 'images', van_slug)
	os.makedirs(van_dir, exist_ok=True)
	
	# Generate unique filename
	import uuid
	filename = f"{uuid.uuid4().hex[:8]}_{file.filename}"
	filepath = os.path.join(van_dir, filename)
	
	try:
		file.save(filepath)
		# Return the URL path
		url_path = f"/static/images/{van_slug}/{filename}"
		return jsonify({"ok": True, "url": url_path, "filename": filename})
	except Exception as e:
		return jsonify({"error": str(e)}), 500

@app.route('/api/admin/upload-about-image', methods=['POST'])
def upload_about_image():
	if not is_admin(request):
		return jsonify({"error": "unauthorized"}), 401

	if 'file' not in request.files:
		return jsonify({"error": "No file provided"}), 400

	file = request.files['file']
	if file.filename == '':
		return jsonify({"error": "No file selected"}), 400

	from werkzeug.utils import secure_filename
	import imghdr
	import uuid

	about_dir = os.path.join(os.path.dirname(__file__), 'static', 'images', 'about')
	os.makedirs(about_dir, exist_ok=True)

	raw_name = secure_filename(file.filename or '')
	# Read file bytes to detect type then rewind the stream
	content = file.read()
	try:
		file.stream.seek(0)
	except Exception:
		pass

	detected = imghdr.what(None, h=content)

	# Build filename with detected extension if necessary
	if raw_name:
		name, ext = os.path.splitext(raw_name)
		if ext:
			filename = f"{uuid.uuid4().hex[:8]}_{name}{ext}"
		else:
			if detected:
				filename = f"{uuid.uuid4().hex[:8]}_{name}.{detected}"
			else:
				filename = f"{uuid.uuid4().hex[:8]}_{name}.png"
	else:
		if detected:
			filename = f"{uuid.uuid4().hex[:8]}.{detected}"
		else:
			filename = f"{uuid.uuid4().hex[:8]}.png"

	filepath = os.path.join(about_dir, filename)

	try:
		file.save(filepath)
		url_path = f"/static/images/about/{filename}"

		# Persist to config
		config = load_config()
		sc = config.setdefault('site_content', {})
		about = sc.setdefault('about', {})
		photos = about.get('photos') or []
		# store photos as objects {url, size}
		entry = { 'url': url_path, 'size': '360px' }
		photos.append(entry)
		about['photos'] = photos
		sc['about'] = about
		config['site_content'] = sc
		save_config(config)
		return jsonify({"ok": True, "url": url_path, "filename": filename, "size": "360px"})
	except Exception as e:
		return jsonify({"error": "Failed to save file: " + str(e)}), 500


@app.route('/api/admin/remove-about-image', methods=['POST'])
def remove_about_image():
	if not is_admin(request):
		return jsonify({"error": "unauthorized"}), 401
	try:
		data = request.get_json(force=True)
		image_url_or_obj = data.get('image_url') or data.get('image')
		if not image_url_or_obj:
			return jsonify({"error": "Image URL required"}), 400

		# extract url string
		if isinstance(image_url_or_obj, dict):
			image_url = image_url_or_obj.get('url')
		else:
			image_url = image_url_or_obj

		if not image_url:
			return jsonify({"error": "Image URL required"}), 400

		filename = image_url.split('/')[-1]
		filepath = os.path.join(os.path.dirname(__file__), 'static', 'images', 'about', filename)
		if os.path.exists(filepath):
			try:
				os.remove(filepath)
			except Exception:
				pass

		# remove from config (photos are objects)
		config = load_config()
		sc = config.get('site_content', {})
		about = sc.get('about', {})
		photos = about.get('photos', []) or []
		new_photos = [p for p in photos if not ((isinstance(p, dict) and p.get('url') == image_url) or (isinstance(p, str) and p == image_url))]
		about['photos'] = new_photos
		sc['about'] = about
		config['site_content'] = sc
		save_config(config)
		return jsonify({"ok": True, "message": "About image removed"})
	except Exception as e:
		return jsonify({"error": str(e)}), 500

@app.route('/api/admin/remove-image', methods=['POST'])
def remove_image():
	if not is_admin(request):
		return jsonify({"error":"unauthorized"}), 401
	
	try:
		data = request.get_json(force=True)
		van_slug = data.get('van_slug')
		image_url = data.get('image_url')
		
		if not van_slug or not image_url:
			return jsonify({"error": "Van slug and image URL required"}), 400
		
		# Extract filename from URL
		filename = image_url.split('/')[-1]
		filepath = os.path.join('static', 'images', van_slug, filename)
		
		# Remove file if it exists
		if os.path.exists(filepath):
			os.remove(filepath)
		
		# Update van photos in config and primary image if needed
		config = load_config()
		for van in config.get('vans', []):
			if van.get('slug') == van_slug:
				photos = van.get('photos', []) or []
				if image_url in photos:
					photos.remove(image_url)
				van['photos'] = photos
				# If the main image points to the removed image or is missing, update it
				main = van.get('imageUrl') or ''
				if (main == image_url) or (main and main not in photos):
					van['imageUrl'] = photos[0] if photos else ''
				break
		
		save_config(config)
		return jsonify({"ok": True, "message": "Image removed successfully"})
	except Exception as e:
		return jsonify({"error": str(e)}), 500

@app.route('/api/admin/update-van', methods=['POST'])
def update_van():
	if not is_admin(request):
		return jsonify({"error":"unauthorized"}), 401
	
	try:
		data = request.get_json(force=True)
		van_slug = data.get('slug')
		updates = data.get('updates', {})
		
		if not van_slug:
			return jsonify({"error": "Van slug required"}), 400
		
		config = load_config()
		vans = config.get('vans', [])
		
		# Find and update the van
		van_found = False
		for i, van in enumerate(vans):
			if van.get('slug') == van_slug:
				# Update the van with new data
				vans[i].update(updates)
				van_found = True
				break
		
		if not van_found:
			return jsonify({"error": "Van not found"}), 404
		
		# Save updated config
		config['vans'] = vans
		save_config(config)
		
		return jsonify({"ok": True, "message": "Van updated successfully"})
	except Exception as e:
		return jsonify({"error": str(e)}), 500

@app.route('/api/admin/create-van', methods=['POST'])
def create_van():
	if not is_admin(request):
		return jsonify({"error":"unauthorized"}), 401
	
	try:
		data = request.get_json(force=True)
		slug = (data.get('slug') or '').strip()
		name = (data.get('name') or '').strip()
		
		if not slug or not name:
			return jsonify({"error": "Slug and name are required"}), 400
		
		# Validate slug format (lowercase, hyphens only)
		import re
		if not re.match(r'^[a-z0-9-]+$', slug):
			return jsonify({"error": "Slug must contain only lowercase letters, numbers, and hyphens"}), 400
		
		config = load_config()
		vans = config.get('vans', [])
		
		# Check if slug already exists
		if any(v.get('slug') == slug for v in vans):
			return jsonify({"error": "A van with this slug already exists"}), 400
		
		# Create new van with default values
		new_van = {
			'slug': slug,
			'name': name,
			'pricePerNight': data.get('pricePerNight', 0),
			'description': data.get('description', ''),
			'imageUrl': data.get('imageUrl', ''),
			'photos': data.get('photos', []),
			'equipment': data.get('equipment', []),
			'airbnbIcalUrl': data.get('airbnbIcalUrl', ''),
			'airbnbUrl': data.get('airbnbUrl', '')
		}
		
		# Add the new van
		vans.append(new_van)
		config['vans'] = vans
		save_config(config)
		
		# Create directory for van images
		van_dir = os.path.join('static', 'images', slug)
		os.makedirs(van_dir, exist_ok=True)
		
		return jsonify({"ok": True, "message": "Van created successfully", "van": new_van})
	except Exception as e:
		return jsonify({"error": str(e)}), 500

@app.route('/api/admin/delete-van', methods=['POST'])
def delete_van():
	if not is_admin(request):
		return jsonify({"error":"unauthorized"}), 401
	
	try:
		data = request.get_json(force=True)
		van_slug = data.get('slug')
		
		if not van_slug:
			return jsonify({"error": "Van slug required"}), 400
		
		config = load_config()
		vans = config.get('vans', [])
		
		# Find and remove the van
		van_found = False
		for i, van in enumerate(vans):
			if van.get('slug') == van_slug:
				vans.pop(i)
				van_found = True
				break
		
		if not van_found:
			return jsonify({"error": "Van not found"}), 404
		
		# Save updated config
		config['vans'] = vans
		save_config(config)
		
		return jsonify({"ok": True, "message": "Van deleted successfully"})
	except Exception as e:
		return jsonify({"error": str(e)}), 500

@app.route('/api/admin/confirm-booking', methods=['POST'])
def confirm_booking():
	if not is_admin(request):
		return jsonify({"error":"unauthorized"}), 401
	
	try:
		data = request.get_json(force=True)
		booking_id = data.get('booking_id')  # We'll use timestamp as ID
		
		if not booking_id:
			return jsonify({"error": "Booking ID required"}), 400
		
		# Load messages and find the booking
		messages = load_messages()
		booking_found = False
		booking_total = 0
		
		for i, msg in enumerate(messages):
			if msg.get('type') == 'booking' and msg.get('ts') == booking_id:
				current_status = msg.get('status', 'pending')
				if current_status == 'pending':
					messages[i]['status'] = 'confirmed'
					booking_total = msg.get('total', 0)
					booking_found = True
					break
				elif current_status == 'confirmed':
					return jsonify({"error": "Booking already confirmed"}), 400
				else:
					return jsonify({"error": "Booking is cancelled"}), 400
		
		if not booking_found:
			return jsonify({"error": "Booking not found"}), 404
		
		# Get booking details for email
		booking = next((msg for msg in messages if msg.get('type') == 'booking' and msg.get('ts') == booking_id), None)
		
		# Save updated messages
		save_messages(messages)
		
		# Update stats with confirmed revenue
		stats = load_stats()
		stats['confirmed_revenue'] = stats.get('confirmed_revenue', 0) + booking_total
		save_stats(stats)
		
		# Send confirmation email to customer
		if booking and booking.get('email'):
			customer_email = booking.get('email')
			van_name = booking.get('slug', '').replace('-', ' ').title()
			
			# Find van's Airbnb link
			config = load_config()
			van = next((v for v in config.get('vans', []) if v.get('slug') == booking.get('slug')), None)
			airbnb_url = ''
			if van:
				ical = van.get('airbnbIcalUrl') or ''
				import re
				m = re.search(r"/ical/(\d+)", ical)
				if m:
					airbnb_url = f"https://www.airbnb.com/rooms/{m.group(1)}"
			
			# Prepare customer confirmation email
			confirmation_body = f"""Great news! Your booking has been confirmed!

Booking Details:
Van: {van_name}
Check-in: {booking.get('start')}
Check-out: {booking.get('end')}
Nights: {booking.get('nights')}
Total: ${booking.get('total', 0):,.2f}

Your Information:
Name: {booking.get('name')}
Email: {booking.get('email')}
Phone: {booking.get('phone', 'Not provided')}

Thank you for choosing MyCamperVans! We're looking forward to your stay.

If you have any questions or need to make changes to your booking,
please don't hesitate to contact us.

Best regards,
MyCamperVans Team"""
			
			# Also send reminder to admin to update Airbnb calendar
			admin_reminder = f"""ACTION NEEDED: Update Airbnb Calendar

A booking has just been confirmed and the Airbnb calendar needs to be updated manually.

Booking Details:
Van: {van_name}
Check-in: {booking.get('start')}
Check-out: {booking.get('end')}
Customer: {booking.get('name')}

Please block these dates on Airbnb immediately to prevent double bookings.
{f'Airbnb Listing: {airbnb_url}' if airbnb_url else 'Please update the appropriate Airbnb listing.'}

Instructions:
1. Log in to your Airbnb host account
2. Go to the listing calendar
3. Block the dates from {booking.get('start')} to {booking.get('end')}
4. Add a note: "Confirmed booking - {booking.get('name')}"

This step is crucial to prevent double bookings!"""
			
			# Send confirmation to customer
			send_email(
				"Your Booking is Confirmed! - MyCamperVans",
				confirmation_body,
				None,
				to_email=customer_email
			)
			
			# Send calendar update reminder to admin
			send_email(
				f"ACTION NEEDED: Update Airbnb Calendar - {van_name} {booking.get('start')}",
				admin_reminder,
				None,
				to_email=None  # This will use the default admin email
			)
		
		return jsonify({"ok": True, "message": "Booking confirmed successfully", "total": booking_total})
	except Exception as e:
		return jsonify({"error": str(e)}), 500

@app.route('/api/admin/undo-booking', methods=['POST'])
def undo_booking():
	if not is_admin(request):
		return jsonify({"error":"unauthorized"}), 401
	
	try:
		data = request.get_json(force=True)
		booking_id = data.get('booking_id')
		
		if not booking_id:
			return jsonify({"error": "Booking ID required"}), 400
		
		# Load messages and find the booking
		messages = load_messages()
		booking_found = False
		booking_total = 0
		
		for i, msg in enumerate(messages):
			if msg.get('type') == 'booking' and msg.get('ts') == booking_id:
				current_status = msg.get('status', 'pending')
				if current_status == 'confirmed':
					messages[i]['status'] = 'pending'
					booking_total = msg.get('total', 0)
					booking_found = True
					break
				else:
					return jsonify({"error": "Booking is not confirmed"}), 400
		
		if not booking_found:
			return jsonify({"error": "Booking not found"}), 404
		
		# Save updated messages
		save_messages(messages)
		
		# Update stats by removing confirmed revenue
		stats = load_stats()
		stats['confirmed_revenue'] = max(0, stats.get('confirmed_revenue', 0) - booking_total)
		save_stats(stats)
		
		return jsonify({"ok": True, "message": "Booking undone successfully", "total": booking_total})
	except Exception as e:
		return jsonify({"error": str(e)}), 500


@app.route("/api/availability")
def availability():
	slug = request.args.get("slug")
	if not slug:
		return jsonify({"error": "missing slug"}), 400
	config = load_config()
	van = next((v for v in config.get("vans", []) if v.get("slug") == slug), None)
	if not van:
		return jsonify({"error": "unknown van" }), 404
	ical_url = van.get("airbnbIcalUrl")
	if not ical_url:
		return jsonify({"busy": []})
	try:
		resp = requests.get(ical_url, timeout=15)
		resp.raise_for_status()
		cal = Calendar.from_ical(resp.text)
		busy = []
		for component in cal.walk():
			if component.name == "VEVENT":
				start = component.get("dtstart").dt
				end = component.get("dtend").dt
				if isinstance(start, datetime):
					start = start.astimezone(tz.UTC)
				if isinstance(end, datetime):
					end = end.astimezone(tz.UTC)
				busy.append({ "start": start.strftime("%Y-%m-%d"), "end": end.strftime("%Y-%m-%d") })
	except Exception as e:
		return jsonify({"error": str(e)}), 500
	return jsonify({"slug": slug, "busy": busy})


@app.route('/api/contact', methods=['POST'])
def contact_submit():
	try:
		payload = request.get_json(force=True)
		name = (payload.get('name') or '').strip()
		email = (payload.get('email') or '').strip()
		message = (payload.get('message') or '').strip()
		if not name or not email or not message:
			return jsonify({"ok": False, "error": "Missing fields"}), 400
		entry = { 'name': name, 'email': email, 'message': message, 'ts': datetime.utcnow().isoformat() + 'Z' }
		save_message(entry)
		body = f"Contact form\nName: {name}\nEmail: {email}\nMessage:\n{message}"
		sent = send_email("New contact form submission", body, "info@mycampervans.com")
		return jsonify({"ok": True, "sent": sent})
	except Exception as e:
		return jsonify({"ok": False, "error": str(e)}), 500


@app.route('/api/book', methods=['POST'])
def book_request():
	try:
		payload = request.get_json(force=True)
		slug = (payload.get('slug') or '').strip()
		start = (payload.get('start') or '').strip()
		end = (payload.get('end') or '').strip()
		nights = int(payload.get('nights') or 0)
		total = float(payload.get('total') or 0)
		customer_email = (payload.get('email') or '').strip()
		customer_name = (payload.get('name') or '').strip()
		customer_phone = (payload.get('phone') or '').strip()
		notes = (payload.get('notes') or '').strip()
		
		if not (slug and start and end and nights > 0):
			return jsonify({"ok": False, "error": "Missing required fields"}), 400
		
		# Validate email if provided
		if customer_email:
			try:
				validate_email(customer_email)
			except EmailNotValidError:
				return jsonify({"ok": False, "error": "Invalid email address"}), 400
		
		vans = load_config().get("vans", [])
		van = next((v for v in vans if v.get('slug') == slug), None)
		van_name = van.get('name') if van else slug
		
		entry = { 
			'type': 'booking', 
			'slug': slug, 
			'start': start, 
			'end': end, 
			'nights': nights, 
			'total': total, 
			'email': customer_email,
			'name': customer_name,
			'phone': customer_phone,
			'notes': notes,
			'status': 'pending',  # pending, confirmed, cancelled
			'ts': datetime.utcnow().isoformat() + 'Z' 
		}
		save_message(entry)
		
		# Enhanced email body
		body = f"""New Booking Request

Van: {van_name} ({slug})
Dates: {start} → {end}
Nights: {nights}
Total: ${total:,.2f}

Customer Details:
Name: {customer_name or 'Not provided'}
Email: {customer_email or 'Not provided'}
Phone: {customer_phone or 'Not provided'}

Additional Notes:
{notes or 'None'}

---
This booking request was submitted from your website.
Please contact the customer to confirm availability and complete the booking."""
		
		# Send notification to admin
		admin_sent = send_email(f"Booking Request: {van_name} - {customer_name or 'Unknown'}", body, customer_email)
		
		# Send confirmation to customer
		customer_body = f"""Thank you for your booking request!

We have received your booking details:

Van: {van_name}
Check-in: {start}
Check-out: {end}
Nights: {nights}
Total: ${total:,.2f}

Your Details:
Name: {customer_name}
Email: {customer_email}
Phone: {customer_phone or 'Not provided'}
Additional Notes: {notes or 'None'}

We will review your request and contact you shortly to confirm the availability and complete the booking process.

Best regards,
MyCamperVans Team"""
		
		customer_sent = send_email("Your Booking Request - MyCamperVans", customer_body, None, to_email=customer_email)
		
		return jsonify({"ok": True, "sent": admin_sent and customer_sent})
	except Exception as e:
		return jsonify({"ok": False, "error": str(e)}), 500


@app.route('/api/checkout', methods=['POST'])
def checkout():
	cfg = load_config().get('stripe', {})
	secret = cfg.get('secretKey')
	public = cfg.get('publicKey')
	if not (stripe and secret and public):
		return jsonify({ 'error': 'Stripe not configured' }), 400
	stripe.api_key = secret
	data = request.get_json(force=True)
	name = data.get('name','Rental')
	amount = int(float(data.get('amount', 0)) * 100)
	currency = (cfg.get('currency') or 'usd')
	if amount <= 0:
		return jsonify({'error':'Invalid amount'}), 400
	try:
		session = stripe.checkout.Session.create(
			mode='payment',
			line_items=[{
				'price_data': {
					'currency': currency,
					'product_data': { 'name': name },
					'unit_amount': amount
				},
				'quantity': 1
			}],
			success_url=data.get('successUrl') or request.host_url + 'vans',
			cancel_url=data.get('cancelUrl') or request.host_url + 'vans'
		)
		return jsonify({ 'url': session.url })
	except Exception as e:
		return jsonify({ 'error': str(e) }), 500


@app.route('/static/<path:path>')
def send_static(path):
	return send_from_directory('static', path)


if __name__ == "__main__":
	port = int(os.environ.get("PORT", 5000))
	app.run(host="0.0.0.0", port=port, debug=True)
