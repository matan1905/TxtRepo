from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader
from db_connection import get_db_connection

api_key_header = APIKeyHeader(name="X-API-Key")

def get_current_user(api_key: str = Depends(api_key_header)):
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE api_key = %s", (api_key,))
    user = cursor.fetchone()
    cursor.close()
    db.close()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key",
        )
    return user