[industry standard]
redis-asyncio
pywt
for password, bcrypt-> argon2-cffi

fastapi-users for auth/
Startups ship with fastapi-users or Auth0/Clerk (external). Large companies build custom (like I am doing) because they need fine-grained control over session semantics, token rotation policies, and audit trails.

asyncpg 
-> sqlalchemy(orm+ pydantic) (industry standard)
-> sqlmodel(wraps sqlalchemy2.0 and pydantic validation)