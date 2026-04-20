from sqlalchemy import Column, String, Integer
from binance_square_bot.models.base import Base, Database

def test_database_init():
    """Test database initialization creates tables."""
    class TestModel(Base):
        __tablename__ = "test_table"
        id = Column(Integer, primary_key=True)
        name = Column(String)

    Database.init(":memory:")

    with Database.get_session() as session:
        # Should be able to create and query
        obj = TestModel(name="test")
        session.add(obj)
        session.commit()

        result = session.query(TestModel).first()
        assert result.name == "test"
