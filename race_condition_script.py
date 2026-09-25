from diafragma.db.base import engine
from diafragma.db.models import Client
from sqlalchemy.orm import sessionmaker

Session = sessionmaker(engine)

with Session() as session:
  for i in range(10):
    client = Client(name=f"Dayvd{i}", phone=f"+552199077585{i}")
    session.add(client)
  session.commit()
