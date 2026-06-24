# since auth files uses .. to get files form backend its needs to be package


"""
How to log?
> use info for every route endpoint, at starting, at end of func using middleware
> use info for lifespan, major milestone with try/except
> use critical in except for major milestone
> use warning in every except if handled
> use error in every except if raised
> use try/except only if
    - there is fallback func to call
    - req logging
    - needs to raise custom error
> use debug only in interanl debugging where ever you want off in prod


AUTH/

cookies.py
-> is imported in 4 files better to create a seperate file for this to avoid
circular dependency

repository.py
> for each table, class to interact and row class
> handles all sql queries part, insert, exits, create into table

tokens.py
> kind of helper, to decode encode tokens,
> TokenPayload defined here, though decode,encode cookies is handled interanlly
> but get_current_user needs to return something, why not make it a object

token_store.py
> redis class, diectly storing retreiving as json
> only those which are send to user and recieved from user needs seperate object
> so that we can inherit pydanctic base model

routes.py
> handles all auth routes, login/logout/signup/
> LoginRequest defined here

services.py (routes -> servies -> repository) this pattern is used for db
> servies raises app error, routes catches it, raise http instead
> this is done to traceback actual error in production
> this file handles combination of direct sql queries need,
> sql must not be used directly in routes endpoint function

dependencies.py
> all those functions which would be called via Depends() in route endpoint
> db, redis connection pool variables, setter, getter functions since
> since all these are called via lifespan dependency of fastapi


DB/
migrations/






"""
