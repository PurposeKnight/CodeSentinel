import hmac
import hashlib
import json
import urllib.request
import sys

# Define payload. We can review pallets/flask, or change this to any public repo.
payload = {
    "action": "opened",
    "number": 5660,
    "pull_request": {
        "number": 5660,
        "head": {
            "sha": "028160e49f9d07f0244bcb149f74fd1946950941"
        },
        "base": {
            "sha": "main"
        }
    },
    "repository": {
        "full_name": "pallets/flask",
        "clone_url": "https://github.com/pallets/flask.git"
    }
}

body = json.dumps(payload).encode('utf-8')
# Matches GITHUB_WEBHOOK_SECRET in .env
secret = b"change-me"
signature = "sha256=" + hmac.new(secret, body, hashlib.sha256).hexdigest()

req = urllib.request.Request(
    "http://localhost:8000/api/v1/webhooks/github",
    data=body,
    headers={
        "Content-Type": "application/json",
        "X-GitHub-Event": "pull_request",
        "X-GitHub-Delivery": "test-pr-flask-5660",
        "X-Hub-Signature-256": signature
    }
)

print("Triggering simulated review for pallets/flask PR #5660...")
try:
    with urllib.request.urlopen(req) as response:
        print("Response Code:", response.getcode())
        print("Response Body:", response.read().decode('utf-8'))
        print("\nSuccess! Open http://localhost:3000 in your browser to see the live scan progress.")
except Exception as e:
    print("Error triggering webhook:", e)
    sys.exit(1)
