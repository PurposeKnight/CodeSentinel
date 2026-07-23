import hmac
import hashlib
import json
import urllib.request
import sys

# Define payload with a clean repository
payload = {
    "action": "opened",
    "number": 1,
    "pull_request": {
        "number": 1,
        "head": {
            "sha": "7fd3ae16b340a63228d150242557ec410fd31853"
        },
        "base": {
            "sha": "master"
        }
    },
    "repository": {
        "full_name": "octocat/Hello-World",
        "clone_url": "https://github.com/octocat/Hello-World.git"
    }
}

body = json.dumps(payload).encode('utf-8')
secret = b"change-me"
signature = "sha256=" + hmac.new(secret, body, hashlib.sha256).hexdigest()

req = urllib.request.Request(
    "http://localhost:8000/api/v1/webhooks/github",
    data=body,
    headers={
        "Content-Type": "application/json",
        "X-GitHub-Event": "pull_request",
        "X-GitHub-Delivery": "test-pr-clean-1",
        "X-Hub-Signature-256": signature
    }
)

print("Triggering simulated review for octocat/Hello-World PR #1...")
try:
    with urllib.request.urlopen(req) as response:
        print("Response Code:", response.getcode())
        print("Response Body:", response.read().decode('utf-8'))
        print("\nSuccess!")
except Exception as e:
    print("Error triggering webhook:", e)
    sys.exit(1)
