import requests
from config import SLACK_WEBHOOK_URL
import logging

def send_slack_alert(caller_id, time_of_call, sheet_link, campaign_name="Unknown", call_type="Unknown"):
    try:
        # Determine emoji and styling based on call type
        if call_type == "0819 Call":
            emoji = "🎯"
            call_type_text = f"*{call_type}*"
        elif call_type == "No Value":
            emoji = "📞"
            call_type_text = f"*{call_type}*"
        else:
            emoji = "📱"
            call_type_text = f"*{call_type}*"
        
        message = {
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"{emoji} *New {call_type_text} Logged*\n\n• *Caller ID:* `{caller_id}`\n• *Time:* `{time_of_call}`\n• *Campaign:* `{campaign_name}`\n• *Type:* {call_type_text}"
                    }
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "📊 View Google Sheet"
                            },
                            "url": sheet_link,
                            "style": "primary"
                        }
                    ]
                }
            ]
        }
        
        response = requests.post(SLACK_WEBHOOK_URL, json=message, timeout=10)
        response.raise_for_status()
        
        logging.info(f"Successfully sent Slack notification for {call_type.lower()} from caller {caller_id}")
        return True
        
    except Exception as e:
        logging.error(f"Error sending Slack notification: {str(e)}")
        return False
