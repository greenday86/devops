import os
import boto3
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_sdk.models.blocks import SectionBlock, DividerBlock, ContextBlock
from slack_sdk.models.blocks.basic_components import MarkdownTextObject

# Slack Bolt 앱 초기화
app = App(token=os.environ.get("SLACK_BOT_TOKEN"))

# 메시지 이벤트 처리
@app.event("message")
def handle_message_events(event, say, logger):
    text = event.get("text", "")
    
    if text.startswith("alb 라우팅"):
        # 메시지 텍스트에서 프로파일명과 ALB 이름을 추출
        parts = text.split()
        if len(parts) >= 3:
            profile = parts[0]
            alb_name = parts[1]
            handle_alb_routing(say, profile, alb_name)
        else:
            say("Please provide a profile name and ALB name. Usage: `alb 라우팅 [profile] [ALB Name]`")

def build_block_kit_for_routing_info(routing_info, alb_name):
    blocks = [
        SectionBlock(
            text=MarkdownTextObject(text=f"*Routing information for ALB: {alb_name}*")
        ),
        DividerBlock()
    ]

    listener_arn_prefix = "arn:aws:elasticloadbalancing:ap-northeast-2:543945541886:listener/app/"
    target_group_arn_prefix = "arn:aws:elasticloadbalancing:ap-northeast-2:543945541886:targetgroup/"

    current_listener = None
    current_rule_name = None

    for row in routing_info:
        protocol_port, listener_arn, rule_name, rule_priority, target_groups = row

        if listener_arn != current_listener:
            current_listener = listener_arn
            blocks.append(DividerBlock())
            blocks.append(
                SectionBlock(
                    fields=[
                        MarkdownTextObject(text=f"*Protocol:Port*: `{protocol_port}`"),
                        MarkdownTextObject(text=f"*Listener ARN*: `{listener_arn.replace(listener_arn_prefix, '')}`"),
                    ]
                )
            )

        if rule_name != current_rule_name:
            current_rule_name = rule_name
            blocks.append(
                SectionBlock(
                    fields=[
                        MarkdownTextObject(text=f"*Rule Name*: `{rule_name}`"),
                        MarkdownTextObject(text=f"*Rule Priority*: `{rule_priority}`")
                    ]
                )
            )

        target_group_list = "\n".join([f"- `{tg.replace(target_group_arn_prefix, '')}` (Weight: {weight})" for tg, weight in target_groups])
        blocks.append(
            SectionBlock(
                text=MarkdownTextObject(text=f"*Target Groups*:\n{target_group_list}")
            )
        )

    return blocks

def handle_alb_routing(say, profile, alb_name):
    try:
        session = boto3.Session(profile_name=profile)
        elbv2_client = session.client('elbv2')

        load_balancers = elbv2_client.describe_load_balancers(Names=[alb_name])
        alb_arn = load_balancers['LoadBalancers'][0]['LoadBalancerArn']

        listeners = elbv2_client.describe_listeners(LoadBalancerArn=alb_arn)
        routing_info = []

        for listener in listeners['Listeners']:
            listener_arn = listener['ListenerArn']
            protocol_port = f"{listener['Protocol']}:{listener['Port']}"

            rules = elbv2_client.describe_rules(ListenerArn=listener['ListenerArn'])

            for rule in rules['Rules']:
                rule_priority = rule['Priority']
                rule_arn = rule['RuleArn']

                rule_tags = elbv2_client.describe_tags(ResourceArns=[rule_arn])
                rule_name = "No Name"
                for tag_description in rule_tags['TagDescriptions']:
                    for tag in tag_description['Tags']:
                        if tag['Key'] == 'Name':
                            rule_name = tag['Value']
                            break

                target_groups = []
                for action in rule['Actions']:
                    if action['Type'] == 'forward':
                        tg_list = action.get('ForwardConfig', {}).get('TargetGroups', [])
                        for tg in tg_list:
                            target_group_arn = tg['TargetGroupArn']
                            weight = tg['Weight']
                            target_groups.append((target_group_arn, weight))

                routing_info.append([protocol_port, listener_arn, rule_name, rule_priority, target_groups])

        if routing_info:
            blocks = build_block_kit_for_routing_info(routing_info, alb_name)
            say(blocks=blocks)
        else:
            say(f"No routing information found for ALB: {alb_name}")

    except Exception as e:
        say(f"Error: {str(e)}")

# Slack Socket Mode 핸들러 시작
if __name__ == "__main__":
    handler = SocketModeHandler(app, os.environ.get("SLACK_APP_TOKEN"))
    handler.start()