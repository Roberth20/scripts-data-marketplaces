from sqlalchemy import create_engine

try:
    from instance import dev
    config = dev
except:
    from instance import test
    config = test

conn = create_engine(f"mysql+pymysql://{config.user}:{config.password}@{config.endpoint}:{config.port}/{config.db}", pool_recycle=7200)