#!/usr/bin/env python
import os
import time
import boto3


def get_cloudformation_params(stackname, region='ca-central-1'):
    cfn = boto3.client('cloudformation', region_name=region)
    return cfn.describe_stacks(StackName=stackname)['Stacks'][0]['Parameters']


def update_stack(stackname, newurl, region='ca-central-1'):
    print("Updating cloudformation: {0}, new: {1}, region={2}".format(
        stackname,
        newurl,
        region)
        )
    cfn = boto3.client('cloudformation', region_name=region)
    params = get_cloudformation_params(stackname, region)
    # change the Param for PrimaryUrl
    for i in params:
        if i['ParameterKey'] == "DomainName":
            i['ParameterValue'] = newurl
    # Issue update stack command
    cfn.update_stack(
        StackName=stackname,
        UsePreviousTemplate=True,
        Parameters=params,
        Capabilities=['CAPABILITY_IAM']
    )


def check_green_light(stackname, region='ca-central-1'):
    cfn = boto3.client('cloudformation', region_name=region)
    status = cfn.describe_stacks(StackName=stackname)['Stacks'][0]['StackStatus']
    if status in ['UPDATE_COMPLETE', 'CREATE_COMPLETE']: # green status!
        return True
    else:
        print("Stackname: {0} is {1}".format(
                stackname,
                status)
                )
        # This is kinda weird. Here we WANT to exit ungracefully so the
        # state machine will "retry"
        raise BaseException


def kicker(event, context):
    print(event)
    '''
    Think about it, if the $current_primary stack ponger is not getting invoked,
    it means that lambda is degraded somewhere. Either in the primary region or
    the standby region. So, it makes sense to then pivot to a [hopefully]
    working region... cross region invocation makes the context of this lambda
    function difficult to understand...

    MyStack = the region I am in (aka, the current standby)
    OtherStack = the other region (aka, the current primary)
    But, at the end of this:
    OtherStack will be the standby
    Mystack will be the primary

    MyStack (current standby) is currently in the way!
    1) update the mystack infra stack to be the transitional url
    2) update the mystack ping-pong stack to be the transitional url
    3) update the otherstack infra stack to be the new standby
    4) update the otherstack ping pong stack to be the new standby
    5) update the mystack infra stack to be the new primary
    6) update the mystack ping-pong stack to be the new primary
    '''

    # Check cooldown status
    # the ttl feature may have latency per the docs so we cannot trust it
    ddb = boto3.client('dynamodb')
    expr = {':date' : {'N': None }}
    expr[':date']['N'] = str(round(time.time()))
    response = ddb.scan(
            TableName=os.environ['CoolDownTableName'],
            FilterExpression="expiretime > :date",
            ExpressionAttributeValues=expr
            )
    if response['Count'] > 0:
        # Oh No, we are still in cooldown.
        print("Still in cooldown, exiting")
        return "Still in cooldown, exiting"

    # Check to see if THIS region is actually the problem..
    cw = boto3.client('cloudwatch')
    response = cw.describe_alarms(
        AlarmNames=[
            os.environ['PingerAlarmName']
        ],
        StateValue='ALARM'
    )
    if response['MetricAlarms']: # is not nil, there IS an alarm
        # Not even sure if this will get invoked if there is a problem in this
        # region, but the behavior is very unknown so it is worth checking.
        print("I think the problem is with this region...undefined")
        return "I think the problem is with this region...undefined, exiting"

    # Write a cooldown timestamp entry into ddb
    # Build the dict to put into ddb
    putitem = {'created': {'N': None}, 'expiretime': { 'N': None } }
    putitem['created']['N'] = str(round(time.time()))
    putitem['expiretime']['N'] = str(round(time.time()) + 900)
    # put the item
    ddb.put_item(
        TableName=os.environ['CoolDownTableName'],
        Item=putitem
    )

    client = boto3.client('stepfunctions')
    print('Invoking StateMachine: {0}'.format(os.environ['StateMachineArn']))
    response = client.start_execution(
            stateMachineArn=os.environ['StateMachineArn']
            )

def FirstFunction(event, context):
    print(event)
    # 1) update the mystack infra stack to be the transitional url
    update_stack(
            os.environ['MyInfraStackName'],
            os.environ['TransitionalUrl'],
            os.environ['AWS_DEFAULT_REGION']
            )

def FirstWait(event, context):
    print(event)
    # Do not pass go until MyInfraStackName is done (route53 takes longer than
    # ping pong stack)
    check_green_light(os.environ['MyInfraStackName'],
            os.environ['AWS_DEFAULT_REGION'])

def SecondFunction(event, context):
    print(event)
    # 2) update the mystack ping-pong stack to be the transitional url
    update_stack(
            os.environ['MyPingPongStackName'],
            os.environ['TransitionalUrl'],
            os.environ['AWS_DEFAULT_REGION']
            )

def ThirdFunction(event, context):
    print(event)
    # 3) update the otherstack infra stack to be the new standby
    update_stack(
            os.environ['OtherInfraStackName'],
            os.environ['StandbyUrl'],
            os.environ['OtherStackRegion']
            )

def ThirdWait(event, context):
    print(event)
    # Do not pass go until OtherInfraStackName is done (route53 takes longer
    # than ping pong stack)
    check_green_light(os.environ['OtherInfraStackName'],
            os.environ['OtherStackRegion'])

def FourthFunction(event, context):
    print(event)
    # 4) update the otherstack ping pong stack to be the new standby
    update_stack(
            os.environ['OtherPingPongStackName'],
            os.environ['StandbyUrl'],
            os.environ['OtherStackRegion']
            )

def FifthFunction(event, context):
    print(event)
    # 5) update the mystack infra stack to be the new primary
    update_stack(
            os.environ['MyInfraStackName'],
            os.environ['PrimaryUrl'],
            os.environ['AWS_DEFAULT_REGION']
            )

def FifthWait(event, context):
    print(event)
    # Do not pass go until MyInfraStackName is done (route53 takes longer than
    # ping pong stack)
    check_green_light(os.environ['MyInfraStackName'],
            os.environ['AWS_DEFAULT_REGION'])

def SixthFunction(event, context):
    print(event)
    # 6) update the mystack ping-pong stack to be the new primary
    update_stack(
            os.environ['MyPingPongStackName'],
            os.environ['PrimaryUrl'],
            os.environ['AWS_DEFAULT_REGION']
            )
