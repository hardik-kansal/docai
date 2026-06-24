# tells python to treat auth as a package/directory
# works without it too, but in some cases might cause module not found error


# sudo systemctl start redis-server
# redis-cli ping -> gives PONG means connection is fine


'''

# depends is a class used with annotated,
#  which is used only with endpoint func called by fastapi
# # which make whenver this function is called, first call this function inside
# and inject the result value
# it automatically forwards the active HTTP request, cookies, and headers into inside func
# without you mapping them manually.
# depends can be used with recursive func tree which is called by fastapi endpoint.

def get_db():
    return Database()

def get_user(db=Depends(get_db)):
    return User(db)

@app.get("/")
def route(user=Depends(get_user)):


# if depends used, func not called by fastapi, then default value is depends() object
# not actually calling func and injecting result

def me(settings: Settings = Depends(get_settings)):
    print(settings)
me()
prints Depends(dependency=<class '__main__.Settings'>, use_cache=True, scope=None)

from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
_bearer_scheme = HTTPBearer()

async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer_scheme)],
    # HTTPAuthorizationCredentials have .credentials (jwt) .scheme (bearer)
) -> TokenPayload:
    """FastAPI dependency — extracts and validates the bearer token."""
    return _decode_token(credentials.credentials)
# annotted[x,y] -> arg: x=y but y is depends class, x is another type thats why used

'''
