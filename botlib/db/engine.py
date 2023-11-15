from sqlalchemy import create_engine
from sqlalchemy.orm.session import sessionmaker
from botlib.paths import database_file


database__url = f"sqlite:///{database_file}"
engine = create_engine(database__url, echo=False)
Session = sessionmaker(bind=engine)
