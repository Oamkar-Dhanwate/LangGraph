import json
import urllib.request

def main():
    # 1. Login
    login_url = "http://127.0.0.1:8000/api/auth/login"
    login_payload = {
        "email": "admin@clientiq.demo",
        "password": "admin123"
    }
    
    req_login = urllib.request.Request(
        login_url,
        data=json.dumps(login_payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req_login, timeout=5) as response:
            res_data = json.loads(response.read().decode())
            print("Login success")
            token = res_data["access_token"]
    except Exception as e:
        print("Login failed:", e)
        if hasattr(e, 'read'):
            print("Login error details:", e.read().decode())
        return

    # 2. Create Company
    create_url = "http://127.0.0.1:8000/api/clients/"
    payload = {
        "name": "Test Company Corp " + str(urllib.request.time.time()),
        "industry": "Technology",
        "account_tier": "silver",
        "size_category": "smb",
        "annual_revenue": 1500000.0,
        "website": "https://testcompany.corp",
        "country": "United States"
    }
    
    req_create = urllib.request.Request(
        create_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        },
        method="POST"
    )
    
    try:
        with urllib.request.urlopen(req_create, timeout=5) as response:
            res_data = json.loads(response.read().decode())
            print("Create Success. Response:")
            print(json.dumps(res_data, indent=2))
    except Exception as e:
        print("Create failed:", e)
        if hasattr(e, 'read'):
            print("Create error details:", e.read().decode())

if __name__ == "__main__":
    import time
    urllib.request.time = time  # Attach time module
    main()
