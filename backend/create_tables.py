from app.database import Base, engine
import app.models


if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    print("Tablolar olusturuldu:", ", ".join(sorted(Base.metadata.tables)))
