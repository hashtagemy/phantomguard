#!/usr/bin/env python3
"""
AWS Configuration Helper for Norn.
Handles both bearer token and IAM credentials authentication.
"""

import os
from typing import Dict, Any, Optional
import boto3
from botocore.config import Config


def get_bedrock_client(region: Optional[str] = None):
    """
    Create a Bedrock Runtime client with proper authentication.
    
    Supports two authentication methods:
    1. Bearer Token (AWS_BEARER_TOKEN_BEDROCK)
    2. IAM Credentials (AWS_ACCESS_KEY_ID + AWS_SECRET_ACCESS_KEY)
    
    Args:
        region: AWS region (defaults to AWS_DEFAULT_REGION env var or us-east-1)
    
    Returns:
        boto3 bedrock-runtime client
    """
    region = region or os.getenv("AWS_DEFAULT_REGION", "us-east-1")
    
    # Check for bearer token first
    bearer_token = os.getenv("AWS_BEARER_TOKEN_BEDROCK")
    
    if bearer_token:
        # Bearer token authentication
        # Bedrock uses the token in the Authorization header
        client = boto3.client(
            "bedrock-runtime",
            region_name=region,
            config=Config(
                signature_version="v4",
                retries={"max_attempts": 3, "mode": "adaptive"},
            ),
        )
        
        # Inject bearer token into client's request headers
        # This is a workaround since boto3 doesn't natively support bearer tokens
        original_make_request = client._make_request
        
        def make_request_with_token(operation_model, request_dict, request_context):
            # Add bearer token to headers
            if "headers" not in request_dict:
                request_dict["headers"] = {}
            request_dict["headers"]["Authorization"] = f"Bearer {bearer_token}"
            return original_make_request(operation_model, request_dict, request_context)
        
        client._make_request = make_request_with_token
        return client
    
    else:
        # Standard IAM credentials authentication
        access_key = os.getenv("AWS_ACCESS_KEY_ID")
        secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
        
        if not access_key or not secret_key:
            raise ValueError(
                "AWS credentials not found. Please set either:\n"
                "  - AWS_BEARER_TOKEN_BEDROCK (for bearer token auth), or\n"
                "  - AWS_ACCESS_KEY_ID + AWS_SECRET_ACCESS_KEY (for IAM auth)"
            )
        
        return boto3.client(
            "bedrock-runtime",
            region_name=region,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            config=Config(
                signature_version="v4",
                retries={"max_attempts": 3, "mode": "adaptive"},
            ),
        )


def get_aws_config() -> Dict[str, Any]:
    """
    Get AWS configuration from environment variables.
    
    Returns:
        Dictionary with AWS configuration
    """
    return {
        "region": os.getenv("AWS_DEFAULT_REGION", "us-east-1"),
        "bearer_token": os.getenv("AWS_BEARER_TOKEN_BEDROCK"),
        "access_key": os.getenv("AWS_ACCESS_KEY_ID"),
        "has_bearer_token": bool(os.getenv("AWS_BEARER_TOKEN_BEDROCK")),
        "has_iam_credentials": bool(
            os.getenv("AWS_ACCESS_KEY_ID") and os.getenv("AWS_SECRET_ACCESS_KEY")
        ),
    }


def test_bedrock_connection() -> bool:
    """
    Test Bedrock connection with current credentials.
    
    Returns:
        True if connection successful, False otherwise
    """
    try:
        client = get_bedrock_client()
        # Try a simple converse call as a connection test
        response = client.converse(
            modelId="us.amazon.nova-2-lite-v1:0",
            messages=[
                {
                    "role": "user",
                    "content": [{"text": "Hello"}]
                }
            ],
            inferenceConfig={"maxTokens": 10, "temperature": 0.0},
        )
        print(f"✅ Bedrock connection successful!")
        print(f"   Model response: {response['output']['message']['content'][0]['text'][:50]}")
        return True
    except Exception as e:
        print(f"❌ Bedrock connection failed: {e}")
        return False


if __name__ == "__main__":
    # Test script
    print("Testing AWS Bedrock connection...")
    print(f"Configuration: {get_aws_config()}")
    test_bedrock_connection()
