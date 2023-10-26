from sqlalchemy import create_engine

try:
    from instance import dev
    config = dev
except:
    from instance import test
    config = test

conn = create_engine(f"mariadb+mariadbconnector://{config.user}:{config.password}@{config.endpoint}:{config.port}/{config.db}")