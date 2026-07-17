
from app.core.security import verify_password

stored_hash = "$2a$12$nSLwPvNcyFqwOzprHYXiLOOH.yyIIziFoVMcJnlU8NB2T1eY.7xvO"

print("Fashions123:", verify_password("Fashions123", stored_hash))
print("fashions123:", verify_password("fashions123", stored_hash))
print("Password123:", verify_password("Password123", stored_hash))