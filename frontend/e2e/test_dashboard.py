import urllib.request, urllib.parse, json

data = urllib.parse.urlencode({"grant_type": "password", "client_id": "aria-web", "username": "asdasd@asfd.com", "password": "123456", "scope": "openid"}).encode("utf-8")
req = urllib.request.Request("http://auth.aria.localhost/auth/realms/aria/protocol/openid-connect/token", data=data)
token = json.loads(urllib.request.urlopen(req).read().decode("utf-8"))["access_token"]

req2 = urllib.request.Request("http://api.aria.localhost/api/dashboard?workspace_id=stc-kuwait", headers={"Authorization": "Bearer " + token})
dash = json.loads(urllib.request.urlopen(req2).read().decode("utf-8"))
print(json.dumps(dash, indent=2))
