import pytest
import time
import boto3
import requests

from localstack.generated import FaultRule
from localstack.sdk.clients import ChaosClient

# Replace with your LocalStack endpoint
LOCALSTACK_ENDPOINT = "http://localhost.localstack.cloud:4566"

# Replace with your LocalStack DynamoDB table name
DYNAMODB_TABLE_NAME = "Products"

# Replace with your Lambda function names
LAMBDA_FUNCTIONS = ["add-product", "get-product", "process-product-events"]

@pytest.fixture(scope="module")
def dynamodb_resource():
    return boto3.resource("dynamodb", endpoint_url=LOCALSTACK_ENDPOINT)

@pytest.fixture(scope="module")
def lambda_client():
    return boto3.client("lambda", endpoint_url=LOCALSTACK_ENDPOINT)

def test_dynamodb_table_exists(dynamodb_resource):
    tables = dynamodb_resource.tables.all()
    table_names = [table.name for table in tables]
    assert DYNAMODB_TABLE_NAME in table_names

def test_lambda_functions_exist(lambda_client):
    functions = lambda_client.list_functions()["Functions"]
    function_names = [func["FunctionName"] for func in functions]
    assert all(func_name in function_names for func_name in LAMBDA_FUNCTIONS)

def initiate_dynamodb_outage() -> FaultRule:
    outage_rule = FaultRule(region="us-east-1", service="dynamodb")
    chaos_client = ChaosClient()
    rules = chaos_client.add_fault_rules(fault_rules=[outage_rule])
    return rules

def check_outage_status(expected_status: FaultRule):
    chaos_client = ChaosClient()
    outage_status = chaos_client.get_fault_rules()
    assert outage_status == expected_status

def stop_dynamodb_outage():
    chaos_client = ChaosClient()
    chaos_client.set_fault_rules(fault_rules=[])
    check_outage_status([])

def test_dynamodb_outage(dynamodb_resource):
    # Initiate DynamoDB outage
    outage_payload = initiate_dynamodb_outage()

    # Make a request to DynamoDB and assert an error
    url = "http://12345.execute-api.localhost.localstack.cloud:4566/dev/productApi"
    headers = {"Content-Type": "application/json"}
    data = {
        "id": "prod-1002",
        "name": "Super Widget",
        "price": "29.99",
        "description": "A versatile widget that can be used for a variety of purposes. Durable, reliable, and affordable.",
    }

    response = requests.post(url, headers=headers, json=data)
    assert "error" in response.text

    # Check if outage is running
    check_outage_status(outage_payload)

    # Stop the outage
    stop_dynamodb_outage()

    # Wait for a few seconds
    # Adding a better retry mechanism is left as an exercise
    time.sleep(60)

    # Query if there are items in DynamoDB table
    table = dynamodb_resource.Table(DYNAMODB_TABLE_NAME)
    response = table.scan()
    items = response["Items"]
