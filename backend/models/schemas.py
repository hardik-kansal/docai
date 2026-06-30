from enum import StrEnum


# ---------------------------------------------------------------------------
# Domain models
# ---------------------------------------------------------------------------
class AccessScope(StrEnum):  # now all eunum values must be string
    """Document-access scopes that map to metadata filters in retrieval."""

    LEGAL = "legal"
    COMPLIANCE = "compliance"
    PROCUREMENT = "procurement"
    ADMIN = "admin"  # can access everything


# When inherit Enum, every variable is now enum type
# s=AccesScope.NAME its an enum object, but value is string
# cant compare directly thats why used StrEnum, which is just a wrapper actual object is still enum
# print(s) gives s.value(legal) which is str, s.name is also str (LEGAL)
# s is enum class object, but now due to strEnum can be used to compare with str directly
# which in fact still possible, but static linters like ruff might not allow
# if try to create accesscope of something not part, automaticaly error
