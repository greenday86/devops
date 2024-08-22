import sys
import os
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from handlers.alb_targetgroup_block_bit import register_alb_targetgroup_handlers
from handlers.cluster_status_block_bit import register_cluster_status_handlers
from handlers.scale_in_out_block_kit import register_scale_in_out_handlers
from handlers.menu_block_kit import register_menu_handlers

def create_app():
    slack_bot_token = os.environ.get("SLACK_BOT_TOKEN")
    slack_app_token = os.environ.get("SLACK_APP_TOKEN")
    
    if not slack_bot_token or not slack_app_token:
        raise ValueError("SLACK_BOT_TOKEN and SLACK_APP_TOKEN must be set in environment variables")
    
    app = App(token=slack_bot_token)
    return app, slack_app_token

def print_all_environment_variables():
    for key, value in os.environ.items():
        print(f"{key}: {value}")

app, slack_app_token = create_app()

register_alb_targetgroup_handlers(app)
register_cluster_status_handlers(app)
register_scale_in_out_handlers(app)
register_menu_handlers(app)

@app.event("message")
def handle_message_events(body, logger):
    logger.info(body)
    print(body)

@app.message("hello")
def message_hello(message, say):
    say(
        blocks=[
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"Hey there <@{message['user']}>!"}, 
                "accessory": {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Click Me"},
                    "action_id": "button_click"
                }
            }
        ],
        text=f"Hey there <@{message['user']}>!"
    )


if __name__ == "__main__":
    print_all_environment_variables()
    handler = SocketModeHandler(app, slack_app_token)
    handler.start()