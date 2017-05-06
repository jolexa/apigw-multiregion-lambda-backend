STACKNAME_BASE="apigw-multiregion-lambda-backend"
PRIMARY_REGION="us-east-2"
PRIMARY_BUCKET="apigw-multiregion-lambda-backend"
STANDBY_REGION="us-west-2"
STANDBY_BUCKET="apigw-multiregion-lambda-backend2"
PRIMARY_URL="apigw-multiregion.jolexa.us"
STANDBY_URL="apigw-multiregion-standby.jolexa.us"
ZONE="jolexa.us."

all: existing-project

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
