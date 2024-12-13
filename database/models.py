from sqlalchemy import Column, Integer, ForeignKey, Boolean, DateTime, func, Text, select, insert, update, Enum, UniqueConstraint
from sqlalchemy.orm import relationship, declarative_base

from database.enums import RequestStatus, ResponseStatus, RotationType

Base = declarative_base()

################
# User storage #
################

class Users(Base):
    __tablename__ = 'users'

    user_id = Column(Integer, primary_key=True, autoincrement=True)
    login = Column(Text, nullable=False)
    password = Column(Text, nullable=False)
    is_admin = Column(Boolean, nullable=False)

###################
# Autosync on/off #
###################

class SyncStatus(Base):
    __tablename__ = 'sync_status'

    sync_on = Column(Boolean, primary_key=True, nullable=False, default=False)

#################
# Proxy related #
#################

class ProxyTypes(Base):
    __tablename__ = 'proxy_types'

    proxy_type_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(Text, nullable=False)

    ports = relationship('Ports', back_populates='proxy_type')


class Geos(Base):
    __tablename__ = 'geos'

    geo_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(Text, nullable=False)

    ports = relationship('Ports', back_populates='geo')


class Sellers(Base):
    __tablename__ = 'sellers'

    seller_id = Column(Integer, primary_key=True, autoincrement=True)
    mark = Column(Text)
    site_link = Column(Text)
    login = Column(Text)
    password = Column(Text)

    ports = relationship('Ports', back_populates='seller')


class Ports(Base):
    __tablename__ = 'ports'

    port_id = Column(Integer, primary_key=True, autoincrement=True)
    proxy_type_id = Column(Integer, ForeignKey('proxy_types.proxy_type_id'))
    ip_version = Column(Integer)
    geo_id = Column(Integer, ForeignKey('geos.geo_id'))
    host = Column(Text)
    socks_port = Column(Integer)
    http_port = Column(Integer)
    login = Column(Text)
    password = Column(Text)
    is_active = Column(Boolean)
    rent_end = Column(DateTime(timezone=True))
    rotation_type = Column(Enum(RotationType))
    rotation_link = Column(Text)
    seller_id = Column(Integer, ForeignKey('sellers.seller_id'))

    proxy_type = relationship('ProxyTypes', back_populates='ports')
    geo = relationship('Geos', back_populates='ports')
    seller = relationship('Sellers', back_populates='ports')
    ip_info = relationship('IPInfo', back_populates='port')
    port_response = relationship('PortResponses', back_populates='port')


class Requests(Base):
    __tablename__ = 'requests'

    request_id = Column(Integer, primary_key=True, autoincrement=True)
    login = Column(Text)
    servername = Column(Text)
    priority = Column(Integer)
    geo = Column(Text)
    ip_version = Column(Integer)
    rent_time = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    status = Column(Enum(RequestStatus))

    response = relationship('Responses', back_populates='parent_request')


class Responses(Base):
    __tablename__ = 'responses'

    response_id = Column(Integer, primary_key=True, autoincrement=True)
    parent_request_id = Column(Integer, ForeignKey('requests.request_id'))
    ip_info_id = Column(Integer, ForeignKey('ip_info.ip_info_id'))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    rent_ended_at = Column(DateTime(timezone=True))
    status = Column(Enum(ResponseStatus))

    parent_request = relationship('Requests', back_populates='response')
    ip_info = relationship('IPInfo', back_populates='response')
    port_response = relationship('PortResponses', back_populates='response')


class Operators(Base):
    __tablename__ = 'operators'

    operator_id = Column(Integer, primary_key=True, autoincrement=True)
    operator = Column(Text, nullable=False, unique=True)

    ip_infos = relationship('IPInfo', back_populates='operator')


class Cities(Base):
    __tablename__ = 'cities'

    city_id = Column(Integer, primary_key=True, autoincrement=True)
    city = Column(Text, nullable=False)
    region = Column(Text, nullable=False)

    ip_infos = relationship('IPInfo', back_populates='city')

    __table_args__ = (UniqueConstraint('city', 'region'),)


class IPInfo(Base):
    __tablename__ = 'ip_info'

    ip_info_id = Column(Integer, primary_key=True, autoincrement=True)
    port_id = Column(Integer, ForeignKey('ports.port_id'))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    ip = Column(Text)
    ip_version = Column(Integer)
    operator_id = Column(Integer, ForeignKey('operators.operator_id'))
    city_id = Column(Integer, ForeignKey('cities.city_id'))

    response = relationship('Responses', back_populates='ip_info')
    port = relationship('Ports', back_populates='ip_info')
    operator = relationship('Operators', back_populates='ip_infos')
    city = relationship('Cities', back_populates='ip_infos')


class PortResponses(Base):
    __tablename__ = 'port_responses'

    port_response_id = Column(Integer, primary_key=True, autoincrement=True)
    port_id = Column(Integer, ForeignKey('ports.port_id'))
    response_id = Column(Integer, ForeignKey('responses.response_id'))
    end_timestamp_utc = Column(DateTime(timezone=True), nullable=False)

    port = relationship('Ports', back_populates='port_response')
    response = relationship('Responses', back_populates='port_response')


async def create_tables():
    from sqlalchemy.ext.asyncio import create_async_engine
    engine = create_async_engine('sqlite+aiosqlite:///../proxy.sqlite', echo=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


#
if __name__ == '__main__':
    import asyncio
    asyncio.run(create_tables())