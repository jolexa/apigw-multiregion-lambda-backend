https://apigw-multiregion-lambda-backend.jolexa.us/
===============
# apigw-mutilregion-lambda-backend

## Motivation
The motivation here is to provide a reference implementation of an API Gateway
that can failover to an alternate region automatically when the AWS Lambda (or
API Gateway) service is degraded. There have been multiple occurrences of
several hour AWS Lambda outages in the recent months. If you built a service on
a single region of AWS Lambda, it would be hard to predict an appropriate SLA.

My goal is to provide a reference implementation that has the following
properties:
* minimal cost
* automated
* serverless
* easy to understand or modify

## What?
There are many components of this solution which make it slightly complex. I
tried to wrap the complexity into a step function so that it was not a
_mono-lambda_ function (a large complex lambda function). The core feature is a
cross region invoke that [hopefully] kicks off a process in a working lambda
region. I admit, this is hard to test thoroughly and we do not fully know what
will or will not be working if lambda is not working. Typically, many services
are degraded if Lambda is degraded.

The [Kicker
Function](https://github.com/jolexa/apigw-mutilregion-lambda-backend/blob/master/lambda/swap.py#L48-L116)
is responsible for "kicking" off the Step Function (state machine). This will be
in a different region than where the alarm is originating (by design). The state
machine then invokes a series of [lambda
functions](https://github.com/jolexa/apigw-mutilregion-lambda-backend/blob/master/lambda/swap.py#L118-L191)
that will first move the "current active" API Gateway to a temp endpoint, then
move the "current standby" to be the new active endpoint, finally move the now
temp endpoint to the new standby. Therefore, it is ready for a switch in the
opposite direction.

The step function is pretty simple, it doesn't utilize many of the features
except retry. The reason for this is because the first implementation was a
_mono-lambda_ function and it was approaching the max timeout of 5 minutes. In
addition, it was spending a large amount of time in idle, sleeping state.

![Architecture Diagram](https://raw.githubusercontent.com/jolexa/apigw-mutilregion-lambda-backend/master/diagram.png)

## How?
The
[Makefile](https://github.com/jolexa/apigw-mutilregion-lambda-backend/blob/master/Makefile)
will deploy multiple CloudFormation stacks. Since this is a reference
implementation, I included one of my [existing
projects](https://github.com/jolexa/aws-apigw-acm) to show how it would work.
The relevant stacks are as follows:

1. [Ping Pong Stack](https://github.com/jolexa/apigw-mutilregion-lambda-backend/blob/master/ping-pong-stack.yml)  
This stack is the entire infrastructure sans the cross region bits below
2. [Ping Pong SNS Alarms Stack](https://github.com/jolexa/apigw-mutilregion-lambda-backend/blob/master/ping-pong-stack-sns-alarms.yml)

There are additional helpers in the Makefile to provision this
[website](https://apigw-multiregion-lambda-backend.jolexa.us/)

#### Theory
I choose to manage the API GW/Lambda/SNS infrastructure inside of CloudFormation
because it represents the most manageable methods available as well as the least
possible way of interfering with existing infrastructure. I actually had a
[pretty custom
script](https://github.com/jolexa/aws-apigw-acm/commit/9a00832a5748a7e2a11b36db3f8569ce166222df)
to manage the custom domain in API Gateway, but AWS then released the
`AWS::ApiGateway::DomainName` which proves only one thing: *Once you build
something missing from AWS, they will release it shortly thereafter*

## Things I learned

To be honest, I learned the most about Step Functions. The reset was just figuring out the proper `boto3` code.
* Step Functions are tricky to get proper syntax (json in yaml, tricky [spec](https://states-language.net/spec.html) to understand, etc)
* Step Functions **seem** expensive because you are charged per transition. I assumed that there was some point that a transition would be cheaper than `sleeping` in Lambda. So check my math:

> Step Functions
> $0.000025 per state transition
>
>Lambda  
>$0.000000208 per 100ms  
>($0.0000002 per request)
>
>$0.000025 = $0.000000208 * x invocations
x = 120

>120 invocations = $0.000024 (lambda requests cost). This is almost the cost of 1 state transition.

>120 * 100ms = 12000ms = 12 seconds

>12 seconds of lambda runtime is equivalent to 1 state transition. Factor in the request costs, 12 seconds of lambda runtime & 120 invocations is equivalent to 2 state transitions. So, 6 seconds is equivalent to 1 state transition.

>Conclusion. If you can get a State Machine to Wait for >6 seconds, it is advantageous to wait there instead of waiting in the lambda runtime.


### Shortcomings
* This is really hard to simulate! I don't know if it works for all edge cases.
  I only **know** that it works for the contrived case.

#### Analysis (Testing)

## Cost

## Questions / Contact
I will be more than happy to answer any questions on GitHub Issues and review
Pull Requests to make this reference even better. Feel free to reach me on
[Twitter](https://twitter.com/jolexa) as well.
