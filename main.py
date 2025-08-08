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

def passes_filter(campaign_name, target_name):
    """Check if the call matches our filter criteria"""
    return (campaign_name == RINGBA_FILTERS["campaign_name"] and 
            target_name == RINGBA_FILTERS["target_name"])

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
        # Log the incoming webhook
        data = request.get_json()
        if not data:
            logging.error("No JSON data received")
            return jsonify({"error": "No JSON data received"}), 400
        
        campaign_name = data.get("campaignName", "")
        target_name = data.get("targetName", "")
        caller_id = data.get("callerId", "Unknown")
        
        logging.info(f"Received webhook: campaignName={campaign_name}, targetName={target_name}")
        
        # Check if this call matches our filter
        if not passes_filter(campaign_name, target_name):
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
        slack_success = send_slack_alert(caller_id, time_of_call, sheet_link)
        if not slack_success:
            logging.error("Failed to send Slack notification")
            # Don't fail the webhook if Slack fails
        
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
