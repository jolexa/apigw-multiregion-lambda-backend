#!/usr/bin/env python

def handler(event, context):
    '''
    - Receive an alarm. determine if the alarm is for the primary or not
    - update the primary infra stack to be the new standby
    - update the primary ping pong stack to be the new standby
    - update the standby infra stack to be the new primary
    - update the standby ping-pong stack to be the new primary
    '''

    '''
    MyStack
    OtherStack
    '''

    print(event)
