# # from fastapi import FastAPI, HTTPException, Depends, status, UploadFile, File, Form
# # from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
# # from pydantic import BaseModel
# # from typing import Optional
# # import jwt
# # from jwt.exceptions import InvalidTokenError
# # import redis
# # from redis.exceptions import ConnectionError
# # import time
# # import os
# # from dotenv import load_dotenv
# # from test2 import BlogSuggestionEngine, BlogSuggestion  # Import your existing engine

# # # Load environment variables
# # load_dotenv()

# # # FastAPI app
# # app = FastAPI(title="Blog Suggestion API", version="1.0.0")

# # # Security: JWT configuration
# # SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key")  # Set in .env
# # ALGORITHM = "HS256"
# # security = HTTPBearer()

# # # Redis for rate limiting
# # redis_client = redis.Redis(host="redis", port=6379, db=0, decode_responses=True)

# # # Pydantic model for JSON input
# # class BlogSuggestInput(BaseModel):
# #     body_markdown: str

# # # Pydantic model for output
# # class BlogSuggestOutput(BaseModel):
# #     titles: list[str]
# #     meta_description: str
# #     slug: str
# #     keywords: list[str]
# #     confidence: float
# #     serp_score: float

# # # JWT authentication dependency
# # async def verify_jwt_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
# #     try:
# #         token = credentials.credentials
# #         payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
# #         user_id = payload.get("sub")
# #         if not user_id:
# #             raise HTTPException(
# #                 status_code=status.HTTP_401_UNAUTHORIZED,
# #                 detail="Invalid token: No user ID",
# #                 headers={"WWW-Authenticate": "Bearer"},
# #             )
# #         return user_id
# #     except InvalidTokenError:
# #         raise HTTPException(
# #             status_code=status.HTTP_401_UNAUTHORIZED,
# #             detail="Invalid or expired token",
# #             headers={"WWW-Authenticate": "Bearer"},
# #         )

# # # Rate limiting dependency
# # def rate_limit(user_id: str):
# #     key = f"rate_limit:{user_id}"
# #     try:
# #         current_count = redis_client.get(key)
# #         current_count = int(current_count) if current_count else 0
        
# #         if current_count >= 30:
# #             raise HTTPException(
# #                 status_code=status.HTTP_429_TOO_MANY_REQUESTS,
# #                 detail="Rate limit exceeded: 30 requests per minute",
# #             )
        
# #         # Increment count and set expiry to 60 seconds if first request
# #         pipe = redis_client.pipeline()
# #         pipe.incr(key)
# #         if current_count == 0:
# #             pipe.expire(key, 60)
# #         pipe.execute()
# #     except ConnectionError:
# #         raise HTTPException(
# #             status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
# #             detail="Redis connection failed",
# #         )

# # # Initialize suggestion engine (load once at startup)
# # engine = BlogSuggestionEngine(dataset_path=r"D:\me\blog_post\medium_post_titles.csv")

# # @app.post("/api/v1/blog/suggest", response_model=BlogSuggestOutput)
# # async def suggest_blog_metadata(
# #     body_markdown: Optional[str] = Form(None),  # Accept body_markdown as form-data
# #     file: Optional[UploadFile] = File(None),   # Accept file upload
# #     tone: Optional[str] = None,
# #     user_id: str = Depends(verify_jwt_token),
# # ):
# #     """
# #     Generate blog title and metadata suggestions.
# #     Accepts either body_markdown (JSON or form-data) or a .md file upload.
# #     Requires JWT authentication and respects rate limiting (30 req/min/user).
# #     """
# #     rate_limit(user_id)  # Apply rate limiting

# #     # Validate input: either body_markdown or file must be provided
# #     if not body_markdown and not file:
# #         raise HTTPException(
# #             status_code=status.HTTP_400_BAD_REQUEST,
# #             detail="Either body_markdown or a file must be provided"
# #         )
# #     if body_markdown and file:
# #         raise HTTPException(
# #             status_code=status.HTTP_400_BAD_REQUEST,
# #             detail="Provide either body_markdown or a file, not both"
# #         )

# #     # Process input
# #     markdown_content = ""
# #     if file:
# #         # Validate file type
# #         if not file.filename.lower().endswith(".md"):
# #             raise HTTPException(
# #                 status_code=status.HTTP_400_BAD_REQUEST,
# #                 detail="File must be a .md file"
# #             )
# #         # Read file content
# #         try:
# #             markdown_content = await file.read()
# #             markdown_content = markdown_content.decode("utf-8")
# #         except Exception as e:
# #             raise HTTPException(
# #                 status_code=status.HTTP_400_BAD_REQUEST,
# #                 detail=f"Failed to read file: {str(e)}"
# #             )
# #     else:
# #         markdown_content = body_markdown

# #     # Validate content
# #     if not markdown_content.strip() or len(markdown_content) < 10:
# #         raise HTTPException(
# #             status_code=status.HTTP_400_BAD_REQUEST,
# #             detail="Markdown content is empty or too short"
# #         )

# #     try:
# #         # Generate suggestions using your engine
# #         suggestions: BlogSuggestion = engine.generate_suggestions(
# #             markdown_content=markdown_content,
# #             tone=tone if tone in ["formal", "casual", "clickbait"] else None
# #         )
        
# #         return {
# #             "titles": suggestions.titles,
# #             "meta_description": suggestions.meta_description,
# #             "slug": suggestions.slug,
# #             "keywords": suggestions.keywords,
# #             "confidence": suggestions.confidence,
# #             "serp_score": suggestions.serp_score
# #         }
# #     except ValueError as e:
# #         raise HTTPException(
# #             status_code=status.HTTP_400_BAD_REQUEST,
# #             detail=str(e)
# #         )
# #     except Exception as e:
# #         raise HTTPException(
# #             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
# #             detail=f"Internal server error: {str(e)}"
# #         )

# # @app.get("/healthz")
# # async def health_check():
# #     """Health check endpoint to verify service dependencies"""
# #     try:
# #         # Check Redis
# #         redis_client.ping()
# #         # Check SQLite (simple query to verify connection)
# #         import sqlite3
# #         conn = sqlite3.connect("/app/data/title_corpus.db")
# #         conn.execute("SELECT 1 FROM titles LIMIT 1")
# #         conn.close()
# #         return {"status": "healthy"}
# #     except (ConnectionError, sqlite3.Error):
# #         raise HTTPException(
# #             status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
# #             detail="Service unhealthy: Failed to connect to Redis or SQLite"
# #         )


from fastapi import FastAPI, HTTPException, Depends, status, UploadFile, File, Form
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional
import jwt
from jwt.exceptions import InvalidTokenError
import redis
from redis.exceptions import ConnectionError
import time
import os
from dotenv import load_dotenv
from test2  import BlogSuggestionEngine, BlogSuggestion  # Import your existing engine

# Load environment variables
load_dotenv()

# FastAPI app
app = FastAPI(title="Blog Suggestion API", version="1.0.0")

# Security: JWT configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "12345")  # Set in .env
ALGORITHM = "HS256"
TOKEN_EXPIRE_SECONDS = 3600  # 1 hour expiration
security = HTTPBearer()

# Redis for rate limiting
# redis_client = redis.Redis(host="redis", port=6379, db=0, decode_responses=True)
# try:
#     redis_client = redis.Redis(
#         host="localhost",  # Changed from "redis" to "localhost"
#         port=6379, 
#         db=0, 
#         decode_responses=True,
#         socket_connect_timeout=5,
#         socket_timeout=5
#     )
#     # Test the connection
#     redis_client.ping()
#     print("✅ Redis connected successfully!")
# except redis.ConnectionError as e:
#     print(f"❌ Redis connection failed: {e}")
#     redis_client = None
redis_client = redis.Redis(
    host=os.getenv("REDIS_HOST", "redis"),  # Use environment variable
    port=int(os.getenv("REDIS_PORT", 6379)),
    db=0, 
    decode_responses=True,
    socket_connect_timeout=5,
    socket_timeout=5
)

# Pydantic model for token generation input
class TokenInput(BaseModel):
    user_id: str

# Pydantic model for JSON input to blog suggestion
class BlogSuggestInput(BaseModel):
    body_markdown: str

# Pydantic model for output
class BlogSuggestOutput(BaseModel):
    titles: list[str]
    meta_description: str
    slug: str
    keywords: list[str]
    confidence: float
    serp_score: float

# JWT authentication dependency
async def verify_jwt_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: No user ID",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return user_id
    except InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

# Rate limiting dependency
def rate_limit(user_id: str):
    key = f"rate_limit:{user_id}"
    try:
        current_count = redis_client.get(key)
        current_count = int(current_count) if current_count else 0
        
        if current_count >= 30:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded: 30 requests per minute",
            )
        
        # Increment count and set expiry to 60 seconds if first request
        pipe = redis_client.pipeline()
        pipe.incr(key)
        if current_count == 0:
            pipe.expire(key, 60)
        pipe.execute()
    except ConnectionError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Redis connection failed",
        )

# Initialize suggestion engine (load once at startup)
# engine = BlogSuggestionEngine(dataset_path=r"D:\me\blog_post\medium_post_titles.csv")
# Change this line to use relative path:
engine = BlogSuggestionEngine(dataset_path="medium_post_titles.csv")

@app.post("/api/v1/token")
async def generate_token(input_data: TokenInput):
    """
    Generate a JWT token for a given user ID.
    Token expires after 1 hour.
    """
    try:
        payload = {
            "sub": input_data.user_id,
            "exp": int(time.time()) + TOKEN_EXPIRE_SECONDS
        }
        token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
        return {"access_token": token, "token_type": "bearer"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate token: {str(e)}"
        )

# @app.post("/api/v1/blog/suggest", response_model=BlogSuggestOutput)
# async def suggest_blog_metadata(
#     body_markdown: Optional[str] = Form(None),  # Accept body_markdown as form-data
#     file: Optional[UploadFile] = File(None),   # Accept file upload
#     tone: Optional[str] = None,
#     user_id: str = Depends(verify_jwt_token),
# ):
#     """
#     Generate blog title and metadata suggestions.
#     Accepts either body_markdown (JSON or form-data) or a .md file upload.
#     Requires JWT authentication and respects rate limiting (30 req/min/user).
#     """
#     rate_limit(user_id)  # Apply rate limiting

#     # Validate input: either body_markdown or file must be provided
#     if not body_markdown and not file:
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="Either body_markdown or a file must be provided"
#         )
#     if body_markdown and file:
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="Provide either body_markdown or a file, not both"
#         )

#     # Process input
#     markdown_content = ""
#     if file:
#         # Validate file type
#         if not file.filename.lower().endswith(".md"):
#             raise HTTPException(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 detail="File must be a .md file"
#             )
#         # Read file content
#         try:
#             markdown_content = await file.read()
#             markdown_content = markdown_content.decode("utf-8")
#         except Exception as e:
#             raise HTTPException(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 detail=f"Failed to read file: {str(e)}"
#             )
#     else:
#         markdown_content = body_markdown

#     # Validate content
#     if not markdown_content.strip() or len(markdown_content) < 10:
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="Markdown content is empty or too short"
#         )

#     try:
#         # Generate suggestions using your engine
#         suggestions: BlogSuggestion = engine.generate_suggestions(
#             markdown_content=markdown_content,
#             tone=tone if tone in ["formal", "casual", "clickbait"] else None
#         )
        
#         return {
#             "titles": suggestions.titles,
#             "meta_description": suggestions.meta_description,
#             "slug": suggestions.slug,
#             "keywords": suggestions.keywords,
#             "confidence": suggestions.confidence,
#             "serp_score": suggestions.serp_score
#         }
#     except ValueError as e:
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail=str(e)
#         )
#     except Exception as e:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Internal server error: {str(e)}"
#         )

@app.post("/api/v1/blog/suggest", response_model=BlogSuggestOutput)
async def suggest_blog_metadata(
    file: Optional[UploadFile] = File(None),   # File upload first
    body_markdown: Optional[str] = Form(None), # Form text second  
    tone: Optional[str] = Form(None),
    user_id: str = Depends(verify_jwt_token),
):
    """
    Generate blog title and metadata suggestions.
    Accepts either body_markdown (form-data) or a .md file upload.
    Requires JWT authentication and respects rate limiting (30 req/min/user).
    """
    rate_limit(user_id)  # Apply rate limiting

    # Debug: Print what we received (remove this in production)
    print(f"DEBUG - file: {file}")
    print(f"DEBUG - file.filename: {getattr(file, 'filename', None) if file else None}")
    print(f"DEBUG - body_markdown: '{body_markdown}'")
    print(f"DEBUG - body_markdown type: {type(body_markdown)}")

    # More robust validation
    has_file = (
        file is not None and 
        hasattr(file, 'filename') and 
        file.filename is not None and 
        file.filename.strip() != "" and
        file.filename != "undefined"  # Common frontend placeholder
    )
    
    has_body_markdown = (
        body_markdown is not None and 
        isinstance(body_markdown, str) and 
        body_markdown.strip() != "" and
        body_markdown.strip() != "null" and  # Common frontend placeholder
        body_markdown.strip() != "undefined"
    )

    print(f"DEBUG - has_file: {has_file}")
    print(f"DEBUG - has_body_markdown: {has_body_markdown}")

    # Validate input: either body_markdown or file must be provided
    if not has_body_markdown and not has_file:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either body_markdown or a file must be provided"
        )
    
    # Allow both if body_markdown is essentially empty - prioritize file
    if has_body_markdown and has_file:
        print("Both provided - prioritizing file upload")
        has_body_markdown = False  # Prioritize file over text

    # Process input
    markdown_content = ""
    
    if has_file:
        print("Processing file upload...")
        # Validate file type
        if not file.filename.lower().endswith(".md"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File must be a .md file"
            )
        # Read file content
        try:
            file_content = await file.read()
            markdown_content = file_content.decode("utf-8")
            print(f"File content length: {len(markdown_content)}")
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to read file: {str(e)}"
            )
    elif has_body_markdown:
        print("Processing body_markdown...")
        markdown_content = body_markdown

    # Validate content
    if not markdown_content or not markdown_content.strip() or len(markdown_content.strip()) < 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Markdown content is empty or too short (minimum 10 characters)"
        )

    print(f"Final content length: {len(markdown_content)}")

    try:
        # Generate suggestions using your engine
        suggestions: BlogSuggestion = engine.generate_suggestions(
            markdown_content=markdown_content,
            tone=tone if tone in ["formal", "casual", "clickbait"] else None
        )
        
        return {
            "titles": suggestions.titles,
            "meta_description": suggestions.meta_description,
            "slug": suggestions.slug,
            "keywords": suggestions.keywords,
            "confidence": suggestions.confidence,
            "serp_score": suggestions.serp_score
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )

# @app.get("/healthz")
# async def health_check():
#     """Health check endpoint to verify service dependencies"""
#     try:
#         # Check Redis
#         redis_client.ping()
#         # Check SQLite (simple query to verify connection)
#         import sqlite3
#         conn = sqlite3.connect("/app/data/title_corpus.db")
#         conn.execute("SELECT 1 FROM titles LIMIT 1")
#         conn.close()
#         return {"status": "healthy"}
#     except (ConnectionError, sqlite3.Error):
#         raise HTTPException(
#             status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
#             detail="Service unhealthy: Failed to connect to Redis or SQLite"
#         )
@app.get("/healthz")
async def health_check():
    """Health check endpoint to verify service dependencies"""
    health_status = {"status": "healthy", "checks": {}}
    overall_healthy = True
    
    # Check Redis
    try:
        if redis_client is not None:
            redis_client.ping()
            health_status["checks"]["redis"] = "healthy"
        else:
            health_status["checks"]["redis"] = "unavailable (skipped)"
    except Exception as e:
        health_status["checks"]["redis"] = f"unhealthy: {str(e)}"
        overall_healthy = False
    
    # Check SQLite - Use the actual path from your engine
    try:
        # Try to check if your BlogSuggestionEngine is working
        # This is more relevant than checking a hardcoded DB path
        if hasattr(engine, 'dataset_path'):
            # Check if the dataset file exists
            import os
            if os.path.exists(engine.dataset_path):
                health_status["checks"]["dataset"] = "healthy"
            else:
                health_status["checks"]["dataset"] = f"dataset not found: {engine.dataset_path}"
                overall_healthy = False
        else:
            health_status["checks"]["dataset"] = "engine not properly initialized"
            overall_healthy = False
            
    except Exception as e:
        health_status["checks"]["dataset"] = f"unhealthy: {str(e)}"
        overall_healthy = False
    
    # Optional: Check if engine can generate suggestions (quick test)
    try:
        # Quick test with minimal content
        test_result = engine.generate_suggestions("# Test\n\nThis is a test.")
        if test_result and hasattr(test_result, 'titles'):
            health_status["checks"]["engine"] = "healthy"
        else:
            health_status["checks"]["engine"] = "engine not responding properly"
            overall_healthy = False
    except Exception as e:
        health_status["checks"]["engine"] = f"unhealthy: {str(e)}"
        overall_healthy = False
    
    # Set overall status
    if not overall_healthy:
        health_status["status"] = "unhealthy"
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Service unhealthy. Checks: {health_status['checks']}"
        )
    
    return health_status


 