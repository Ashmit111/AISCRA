"""
Notification Utilities
Sends alerts via Email (SendGrid) and Slack webhooks
"""

import logging
import json
from typing import Dict, Any, List, Optional
import requests

from ..utils.config import settings

logger = logging.getLogger(__name__)


def send_slack_notification(alert: Dict[str, Any]) -> bool:
    """
    Send alert to Slack via webhook
    
    Args:
        alert: Alert document
    
    Returns:
        True if sent successfully
    """
    webhook_url = settings.slack_webhook_url
    
    if not webhook_url or webhook_url == "your_slack_webhook_url_here":
        logger.warning("Slack webhook URL not configured, skipping notification")
        return False
    
    try:
        # Build Slack message
        severity_emoji = {
            "critical": "🚨",
            "high": "⚠️",
            "medium": "⚡",
            "low": "ℹ️"
        }
        
        emoji = severity_emoji.get(alert.get("severity_band", "medium"), "⚡")
        
        # Format alternates
        alternates_text = ""
        if alert.get("recommendations"):
            alternates_text = "\n\n*Top Alternates:*\n"
            for i, alt in enumerate(alert["recommendations"][:3], 1):
                alternates_text += (
                    f"{i}. *{alt['name']}* ({alt['country']}) - "
                    f"Score: {alt['score']}/10, "
                    f"Lead: {alt['lead_time_weeks']}w\n"
                )
        
        recommendation = alert.get("recommendation_text", "")
        if recommendation:
            recommendation = f"\n\n*Recommendation:*\n{recommendation}"
        
        message = {
            "text": f"{emoji} Supply Chain Risk Alert",
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"{emoji} {alert['title']}"
                    }
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*Severity:*\n{alert['severity_band'].upper()}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Risk Score:*\n{alert['risk_score']:.2f}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Supplier:*\n{alert['affected_supplier']}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Material:*\n{alert['affected_material']}"
                        }
                    ]
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Description:*\n{alert['description']}"
                    }
                }
            ]
        }
        
        # Add alternates if available
        if alternates_text:
            message["blocks"].append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": alternates_text
                }
            })
        
        # Add recommendation if available
        if recommendation:
            message["blocks"].append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": recommendation
                }
            })
        
        # Send to Slack
        response = requests.post(
            webhook_url,
            json=message,
            timeout=10
        )
        
        if response.status_code == 200:
            logger.info(f"✓ Sent Slack notification for alert {alert.get('_id', 'unknown')}")
            return True
        else:
            logger.error(f"Slack notification failed: {response.status_code} {response.text}")
            return False
    
    except Exception as e:
        logger.error(f"Error sending Slack notification: {e}", exc_info=True)
        return False


def send_email_notification(alert: Dict[str, Any]) -> bool:
    """
    Send alert via email using SendGrid
    
    Args:
        alert: Alert document
    
    Returns:
        True if sent successfully
    """
    sendgrid_key = settings.sendgrid_api_key
    
    if not sendgrid_key or sendgrid_key == "your_sendgrid_api_key_here":
        logger.warning("SendGrid API key not configured, skipping email")
        return False
    
    try:
        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import Mail
        
        # Build email content
        severity_color = {
            "critical": "#DC2626",
            "high": "#EA580C",
            "medium": "#F59E0B",
            "low": "#10B981"
        }
        
        color = severity_color.get(alert.get("severity_band", "medium"), "#F59E0B")
        
        # Format alternates HTML
        alternates_html = ""
        if alert.get("recommendations"):
            alternates_html = "<h3>Top Alternate Suppliers</h3><ul>"
            for alt in alert["recommendations"][:3]:
                alternates_html += (
                    f"<li><strong>{alt['name']}</strong> ({alt['country']}) - "
                    f"Score: {alt['score']}/10, "
                    f"Lead time: {alt['lead_time_weeks']} weeks, "
                    f"{'✓ Approved' if alt.get('approved_vendor') else '○ Not approved'}</li>"
                )
            alternates_html += "</ul>"
        
        recommendation_html = ""
        if alert.get("recommendation_text"):
            recommendation_html = f"<h3>Recommendation</h3><p>{alert['recommendation_text']}</p>"
        
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; padding: 20px;">
            <div style="border-left: 4px solid {color}; padding-left: 20px;">
                <h1 style="color: {color};">{alert['title']}</h1>
                <p><strong>Severity:</strong> {alert['severity_band'].upper()}</p>
                <p><strong>Risk Score:</strong> {alert['risk_score']:.2f}</p>
                <p><strong>Affected Supplier:</strong> {alert['affected_supplier']}</p>
                <p><strong>Affected Material:</strong> {alert['affected_material']}</p>
                <h3>Description</h3>
                <p>{alert['description']}</p>
                {alternates_html}
                {recommendation_html}
            </div>
            <hr style="margin-top: 30px;">
            <p style="color: #666; font-size: 12px;">
                Supply Chain Risk Analysis System | Generated: {alert.get('created_at', 'N/A')}
            </p>
        </body>
        </html>
        """
        
        message = Mail(
            from_email=settings.notification_email_from,
            to_emails=settings.notification_email_to,
            subject=f"[{alert['severity_band'].upper()}] {alert['title']}",
            html_content=html_content
        )
        
        sg = SendGridAPIClient(sendgrid_key)
        response = sg.send(message)
        
        if response.status_code in [200, 201, 202]:
            logger.info(f"✓ Sent email notification for alert {alert.get('_id', 'unknown')}")
            return True
        else:
            logger.error(f"Email notification failed: {response.status_code}")
            return False
    
    except ImportError:
        logger.error("SendGrid library not installed. Install with: pip install sendgrid")
        return False
    except Exception as e:
        logger.error(f"Error sending email notification: {e}", exc_info=True)
        return False


def send_alert_notifications(alert: Dict[str, Any], db: Any) -> bool:
    """
    Send alert via all configured notification channels
    
    Args:
        alert: Alert document
        db: MongoDB database instance
    
    Returns:
        True if at least one notification sent successfully
    """
    slack_sent = send_slack_notification(alert)
    email_sent = send_email_notification(alert)
    
    success = slack_sent or email_sent
    
    if success:
        # Update alert to mark notification as sent
        from datetime import datetime
        db.alerts.update_one(
            {"_id": alert["_id"]},
            {
                "$set": {
                    "notification_sent": True,
                    "notification_sent_at": datetime.utcnow()
                }
            }
        )
    
    return success


def send_batch_notifications(alerts: List[Dict[str, Any]], db: Any) -> int:
    """
    Send notifications for multiple alerts
    
    Args:
        alerts: List of alert documents
        db: MongoDB database instance
    
    Returns:
        Number of successful notifications
    """
    sent_count = 0
    
    for alert in alerts:
        try:
            if send_alert_notifications(alert, db):
                sent_count += 1
        except Exception as e:
            logger.error(f"Error sending notification for alert: {e}")
            continue
    
    logger.info(f"Sent {sent_count}/{len(alerts)} notifications")
    
    return sent_count
