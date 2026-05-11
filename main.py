
import os
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from retrieval import process_document, query_active_document, delete_active_document
from database import SessionLocal, UserDB
from auth import get_current_user, authenticate_user, create_access_token, get_db, UserCreate, get_password_hash

app = FastAPI()

@app.post("/register")
async def register(user: UserCreate, db: Session = Depends(get_db)):
    if db.query(UserDB).filter(UserDB.username == user.username).first():
        raise HTTPException(status_code=400, detail="Username already exists")
    hashed = get_password_hash(user.password)
    db_user = UserDB(username=user.username, email=user.email, full_name=user.full_name, hashed_password=hashed)
    db.add(db_user)
    db.commit()
    return {"message": "User registered"}

@app.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user: 
        raise HTTPException(status_code=401,detail="Invalid cridentials")
    return {"access_token": create_access_token(data={"sub": user.username}), "token_type": "bearer"}

# ---  Document Flow ---

@app.post("/upload")
async def upload_document(file: UploadFile = File(...), user: UserDB = Depends(get_current_user)):
    if not (file.filename.endswith(".pdf") or file.filename.endswith(".txt")):
        raise HTTPException(status_code=400, detail="Invalid file type. Only PDF and TXT allowed.")
    temp_path = f"temp_{user.username}_{file.filename}"
    with open(temp_path, "wb") as f:
        f.write(await file.read())
    
    try:
        process_document(temp_path, file.filename, user.username)
        return {"message": "New document uploaded."}
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

@app.post("/chat")
async def chat(query: str, user: UserDB = Depends(get_current_user)):
    answer, sources = query_active_document(query, user.username)
    return {
        "answer": answer,
        "sources": [s.metadata for s in sources] if sources else []
    }

@app.delete("/document")
async def clear_document(user: UserDB = Depends(get_current_user)):
    if delete_active_document(user.username):
        return {"message": "Document deleted successfully."}
    raise HTTPException(status_code=404, detail="No document found to delete.")