import importlib
modules = [
 'fastapi','uvicorn','pydantic','sqlalchemy','alembic','psycopg2','neo4j','redis',
 'celery','transformers','torch','spacy','sklearn','langdetect','datasketch','rapidfuzz',
 'joblib','loguru','requests','PIL','pytesseract','thefuzz','faker','numpy'
]
for m in modules:
    try:
        importlib.import_module(m)
        print('OK',m)
    except Exception as e:
        print('ERR',m,type(e).__name__,e)
