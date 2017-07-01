STACKNAME_BASE="apigw-multiregion-lambda-backend"
PRIMARY_REGION="us-east-2"
PRIMARY_BUCKET="apigw-multiregion-lambda-backend"
STANDBY_REGION="us-west-2"
STANDBY_BUCKET="apigw-multiregion-lambda-backend2"
PRIMARY_URL="apigw-multiregion.jolexa.us"
STANDBY_URL="apigw-multiregion-standby.jolexa.us"
TRANSITIONAL_URL="apigw-multiregion-temp.jolexa.us"
ZONE="jolexa.us."

all: existing-project ping-pong-stack

existing-project:
	cd aws-apigw-acm/ && \
		make \
			STACKNAME_BASE=$(STACKNAME_BASE)-primary \
			REGION=$(PRIMARY_REGION) \
			URL=$(PRIMARY_URL) \
			ZONE=$(ZONE) \
			BUCKET=$(PRIMARY_BUCKET) && \
		make \
			STACKNAME_BASE=$(STACKNAME_BASE)-standby \
			REGION=$(STANDBY_REGION) \
			URL=$(STANDBY_URL) \
			ZONE=$(ZONE) \
			BUCKET=$(STANDBY_BUCKET)

ping-pong-stack:
	cd lambda && zip -r9 deployment.zip *.py && \
		aws s3 cp ./deployment.zip \
		s3://$(PRIMARY_BUCKET)/$(shell md5sum lambda/*.py| md5sum | cut -d ' ' -f 1) && \
		aws s3 cp ./deployment.zip \
		s3://$(STANDBY_BUCKET)/$(shell md5sum lambda/*.py| md5sum | cut -d ' ' -f 1) && \
		rm -f deployment.zip
	cd aws-apigw-acm/ && \
		make \
			STACKNAME_BASE=$(STACKNAME_BASE)-transitional \
			URL=$(TRANSITIONAL_URL) \
			deploy-acm
	aws cloudformation deploy \
		--template-file ping-pong-stack.yml \
		--stack-name $(STACKNAME_BASE)-ping-pong-infra-primary \
		--region $(PRIMARY_REGION) \
		--parameter-overrides \
		"Bucket=$(PRIMARY_BUCKET)" \
		"md5=$(shell md5sum lambda/*.py| md5sum | cut -d ' ' -f 1)" \
		"DomainName=$(PRIMARY_URL)" \
		"PrimaryUrl=$(PRIMARY_URL)" \
		"StandbyUrl=$(Standby_URL)" \
		"TranstionalUrl=$(Transitional_URL)" \
		"MyInfraStrackName=$(STACKNAME_BASE)-primary" \
		"OtherInfraStrackName=$(STACKNAME_BASE)-standby" \
		"OtherPingPongStackName=$(STACKNAME_BASE)-ping-pong-infra-standby" \
		--capabilities CAPABILITY_IAM || exit 0
	aws cloudformation deploy \
		--template-file ping-pong-stack.yml \
		--stack-name $(STACKNAME_BASE)-ping-pong-infra-standby \
		--region $(STANDBY_REGION) \
		--parameter-overrides \
		"Bucket=$(STANDBY_BUCKET)" \
		"md5=$(shell md5sum lambda/*.py| md5sum | cut -d ' ' -f 1)" \
		"DomainName=$(STANDBY_URL)" \
		"PrimaryUrl=$(PRIMARY_URL)" \
		"StandbyUrl=$(Standby_URL)" \
		"TranstionalUrl=$(Transitional_URL)" \
		"MyInfraStrackName=$(STACKNAME_BASE)-standby" \
		"OtherPingPongStackName=$(STACKNAME_BASE)-ping-pong-infra-primary" \
		"OtherInfraStrackName=$(STACKNAME_BASE)-primary" \
		--capabilities CAPABILITY_IAM || exit 0
	aws cloudformation deploy \
		--template-file ping-pong-stack-sns-alarms.yml \
		--stack-name $(STACKNAME_BASE)-ping-pong-infra-primary-sns-alarms \
		--region $(PRIMARY_REGION) \
		--parameter-overrides \
		"OtherRegion=$(STANDBY_REGION)" \
		--capabilities CAPABILITY_IAM || exit 0
	aws cloudformation deploy \
		--template-file ping-pong-stack-sns-alarms.yml \
		--stack-name $(STACKNAME_BASE)-ping-pong-infra-standby-sns-alarms \
		--region $(STANDBY_REGION) \
		--parameter-overrides \
		"OtherRegion=$(PRIMARY_REGION)" \
		--capabilities CAPABILITY_IAM || exit 0
