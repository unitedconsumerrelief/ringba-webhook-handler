import datetime
import json
import logging
from flask import Flask, request, jsonify
from google_sheets import append_row_to_sheet
from slack_notify import send_slack_alert
from config import RINGBA_FILTERS, GOOGLE_SHEET_ID, FLASK_DEBUG, HOST, PORT

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ringba_webhook.log'),
        logging.StreamHandler()
    ]
)

app = Flask(__name__)

def passes_filter(campaign_name, target_name, call_length_from_connect=None, end_call_source=None):
    """Check if the call matches our filter criteria.

    A call is considered "No Value" if:
    - campaign matches, and
    - call_length_from_connect is 0 or empty string, or
    - target_name is empty string, or
    - end_call_source == "system"
    Fallback: if target_name matches configured target_name exactly.
    """
    if campaign_name != RINGBA_FILTERS["campaign_name"]:
        return False

    # Rule 1: Call length from connect equals zero OR is empty string
    if call_length_from_connect is not None:
        # Handle empty string case (Ringba sends "" for No Value calls)
        if str(call_length_from_connect).strip() == "":
            return True
        
        try:
            length_num = float(str(call_length_from_connect).strip())
            if length_num == 0:
                return True
        except ValueError:
            pass

    # Rule 2: Target name is empty string (Ringba sends "" for No Value calls)
    if target_name is not None and str(target_name).strip() == "":
        return True

    # Rule 3: End call source equals "system"
    if end_call_source is not None:
        if str(end_call_source).strip().lower() == "system":
            return True

    # Fallback rule: exact target name match
    return target_name == RINGBA_FILTERS["target_name"]

@app.route("/", methods=["GET"])
def health_check():
    return jsonify({
        "status": "healthy",
        "service": "Ringba Webhook Handler",
        "filters": RINGBA_FILTERS,
        "server": "render"
    }), 200

@app.route("/ringba-webhook", methods=["POST"])
def ringba_webhook():
    try:
        # Handle Slack URL verification challenge
        data = request.get_json()
        if data and data.get("type") == "url_verification":
            challenge = data.get("challenge")
            if challenge:
                return jsonify({"challenge": challenge}), 200
        
        # Log all request details
        content_type = request.headers.get('Content-Type', '')
        content_length = request.headers.get('Content-Length', '0')
        user_agent = request.headers.get('User-Agent', '')
        
        logging.info(f"=== NEW WEBHOOK REQUEST ===")
        logging.info(f"Content-Type: '{content_type}'")
        logging.info(f"Content-Length: '{content_length}'")
        logging.info(f"User-Agent: '{user_agent}'")
        logging.info(f"Request Headers: {dict(request.headers)}")
        
        # Check if request has any data
        raw_data = request.data
        logging.info(f"Raw data length: {len(raw_data)} bytes")
        
        if len(raw_data) == 0:
            logging.warning("Request has no data - empty body. This might be a Ringba configuration issue.")
            return jsonify({
                "status": "received",
                "message": "Empty request received - check Ringba webhook configuration",
                "expected_format": {
                    "campaignName": "SPANISH DEBT | 3.5 STANDARD | 01292025",
                    "targetName": "-no value- or actual target",
                    "callerId": "example_caller_id",
                    "callLengthFromConnect": 0,
                    "endCallSource": "system"
                }
            }), 200
        
        # Try to decode and log the raw data
        try:
            raw_text = raw_data.decode('utf-8')
            logging.info(f"Raw data: '{raw_text}'")
        except Exception as e:
            logging.error(f"Could not decode raw data: {str(e)}")
            return jsonify({"error": "Invalid request encoding"}), 400
        
        # Try to parse JSON
        data = None
        if 'application/json' in content_type:
            data = request.get_json()
        else:
            try:
                data = request.get_json(force=True)
            except:
                try:
                    data = json.loads(raw_text)
                except Exception as e:
                    logging.error(f"Could not parse JSON. Raw text: '{raw_text}', Error: {str(e)}")
                    return jsonify({"error": "Invalid JSON data"}), 400
        
        if not data:
            logging.error("No JSON data received")
            return jsonify({"error": "No JSON data received"}), 400
        
        campaign_name = data.get("campaignName", "")
        target_name = data.get("targetName", "")
        caller_id = data.get("callerId", "Unknown")
        call_length_from_connect = data.get("callLengthFromConnect", data.get("CallLengthFromConnect", data.get("call_length_from_connect")))
        end_call_source = data.get("endCallSource", data.get("EndCallSource", data.get("end_call_source")))
        
        logging.info(f"Parsed data: campaignName='{campaign_name}', targetName='{target_name}', callerId='{caller_id}', callLengthFromConnect='{call_length_from_connect}', endCallSource='{end_call_source}'")
        
        # Check if this call matches our filter
        if not passes_filter(campaign_name, target_name, call_length_from_connect, end_call_source):
            logging.info(f"Call filtered out: campaignName={campaign_name}, targetName={target_name}")
            return jsonify({"status": "filtered", "message": "Call does not match filter criteria"}), 200
        
        # Process the call
        time_of_call = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
        
        # Append to Google Sheet
        sheet_success = append_row_to_sheet(time_of_call, caller_id)
        if not sheet_success:
            logging.error("Failed to append to Google Sheet")
            return jsonify({"error": "Failed to update Google Sheet"}), 500
        
        # Send Slack notification
        sheet_link = f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEET_ID}"
        slack_success = send_slack_alert(caller_id, time_of_call, sheet_link, campaign_name)
        if not slack_success:
            logging.error("Failed to send Slack notification")
        
        logging.info(f"Successfully processed call from {caller_id}")
        
        return jsonify({
            "caller_id": caller_id,
            "status": "success",
            "time": time_of_call
        }), 200
        
    except Exception as e:
        logging.error(f"Error processing webhook: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

if __name__ == "__main__":
    logging.info(f"Starting Ringba Webhook Handler on {HOST}:{PORT}")
    app.run(
        host=HOST,
        port=PORT,
        debug=FLASK_DEBUG
    )
