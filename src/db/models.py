from sqlalchemy import Column, Integer, String, TIMESTAMP, SmallInteger, BigInteger, JSON, Boolean, Float, ForeignKey, Enum as ENUM
from sqlalchemy.orm import declarative_base, relationship
from dateutil.parser import isoparse
from enum import Enum

class SideEnum(Enum):
    BID = "B"
    ASK = "S"

class SnapshotTypeEnum(Enum):
    INIT = "init"
    GAP = "gap"
    SCHEDULED = "scheduled"

Base = declarative_base()

class PriceChange(Base):
    __tablename__ = "price_changes"

    time = Column(TIMESTAMP, primary_key=True)
    market_id = Column(String, primary_key=True)
    price = Column(SmallInteger, primary_key=True)
    size = Column(BigInteger)
    side = Column(ENUM(SideEnum))

class BookSnapshot(Base):
    __tablename__ = "book_snapshots"

    time = Column(TIMESTAMP, primary_key=True)
    market_id = Column(String, primary_key=True)
    snapshot_type = Column(ENUM(SnapshotTypeEnum)) # either init, trade or scheduled
    book = Column(JSON) #json with structure {"bids":[(price, qty), ...], "asks":[(price, qty), ...] }

class TickSizeChange(Base):
    __tablename__ = "tick_size_changes"

    time = Column(TIMESTAMP, primary_key=True)
    market_id = Column(String, primary_key=True)
    tick_size = Column(SmallInteger)

# Define the Event model
class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String)
    slug = Column(String)
    title = Column(String)
    description = Column(String)
    resolutionSource = Column(String)
    startDate = Column(TIMESTAMP)
    creationDate = Column(TIMESTAMP)
    endDate = Column(TIMESTAMP)
    image = Column(String)
    icon = Column(String)
    active = Column(Boolean)
    closed = Column(Boolean)
    archived = Column(Boolean)
    new = Column(Boolean)
    featured = Column(Boolean)
    featuredOrder = Column(Integer)
    restricted = Column(Boolean)
    liquidity = Column(Float)
    volume = Column(Float)
    openInterest = Column(Integer)
    sortBy = Column(String)
    createdAt = Column(TIMESTAMP)
    updatedAt = Column(TIMESTAMP)
    competitive = Column(Float)
    volume24hr = Column(Float)
    enableOrderBook = Column(Boolean)
    liquidityClob = Column(Float)
    negRisk = Column(Boolean)
    negRiskMarketID = Column(String)
    commentCount = Column(Integer)
    cyom = Column(Boolean)
    showAllOutcomes = Column(Boolean)
    showMarketImages = Column(Boolean)
    enableNegRisk = Column(Boolean)
    gmpChartMode = Column(String)
    negRiskAugmented = Column(Boolean)
    liquidityAmm = Column(Float, nullable=True) #added liquidityAmm column
    automaticallyActive = Column(Boolean, nullable=True)
    chatChannelStartTime = Column(TIMESTAMP, nullable=True)
    closedTime = Column(TIMESTAMP, nullable=True)
    color = Column(String, nullable=True)
    countryName = Column(String, nullable=True)
    elapsed = Column(Integer, nullable=True) # or Float if needed
    electionType = Column(String, nullable=True)
    ended = Column(Boolean, nullable=True)
    eventDate = Column(TIMESTAMP, nullable=True)
    eventWeek = Column(Integer, nullable=True)
    finishedTimestamp = Column(TIMESTAMP, nullable=True)
    live = Column(Boolean, nullable=True)
    liveChatChannelId = Column(String, nullable=True)
    negRiskFeeBips = Column(Integer, nullable=True)
    period = Column(String, nullable=True)
    score = Column(String, nullable=True)
    series = Column(JSON, nullable=True)
    seriesSlug = Column(String, nullable=True)
    startTime = Column(TIMESTAMP, nullable=True)
    tweetCount = Column(Integer, nullable=True)
    markets = relationship("Market", back_populates="event")

# Define the Market model
class Market(Base):
    __tablename__ = "markets"

    id = Column(Integer, primary_key=True, index=True)
    question = Column(String)
    conditionId = Column(String)
    slug = Column(String)
    resolutionSource = Column(String)
    endDate = Column(TIMESTAMP)
    liquidity = Column(Float)
    startDate = Column(TIMESTAMP)
    image = Column(String)
    icon = Column(String)
    description = Column(String)
    outcomes = Column(String)
    outcomePrices = Column(String)
    volume = Column(Float)
    active = Column(Boolean)
    closed = Column(Boolean)
    marketMakerAddress = Column(String)
    createdAt = Column(TIMESTAMP)
    updatedAt = Column(TIMESTAMP)
    new = Column(Boolean)
    featured = Column(Boolean)
    submitted_by = Column(String)
    archived = Column(Boolean)
    resolvedBy = Column(String)
    restricted = Column(Boolean)
    groupItemTitle = Column(String)
    groupItemThreshold = Column(String)
    questionID = Column(String)
    enableOrderBook = Column(Boolean)
    orderPriceMinTickSize = Column(Float)
    orderMinSize = Column(Integer)
    volumeNum = Column(Float)
    liquidityNum = Column(Float)
    endDateIso = Column(String)
    startDateIso = Column(String)
    hasReviewedDates = Column(Boolean)
    volume24hr = Column(Float)
    umaBond = Column(String)
    umaReward = Column(String)
    volume24hrClob = Column(Float)
    volumeClob = Column(Float)
    liquidityClob = Column(Float)
    acceptingOrders = Column(Boolean)
    negRisk = Column(Boolean)
    negRiskMarketID = Column(String)
    negRiskRequestID = Column(String)
    eventId = Column(Integer, ForeignKey('events.id'))
    event = relationship("Event", back_populates="markets")
    ready = Column(Boolean)
    funded = Column(Boolean)
    acceptingOrdersTimestamp = Column(TIMESTAMP)
    cyom = Column(Boolean)
    competitive = Column(Float)
    pagerDutyNotificationEnabled = Column(Boolean)
    approved = Column(Boolean)
    clobRewards = Column(JSON)
    rewardsMinSize = Column(Integer)
    rewardsMaxSpread = Column(Float)
    oneDayPriceChange = Column(Float, nullable=True)
    spread = Column(Float)
    lastTradePrice = Column(Float)
    bestBid = Column(Float)
    bestAsk = Column(Float)
    automaticallyActive = Column(Boolean)
    clearBookOnStart = Column(Boolean)
    seriesColor = Column(String)
    showGmpSeries = Column(Boolean)
    showGmpOutcome = Column(Boolean)
    manualActivation = Column(Boolean)
    negRiskOther = Column(Boolean)
    liquidityAmm = Column(Float, nullable=True) #added liquidityAmm column
    volume24hrAmm = Column(Float, nullable=True) #added volume24hrAmm column
    volumeAmm = Column(Float, nullable=True) #added volumeAmm column
    umaResolutionStatus = Column(String, nullable=True)
    gameStartTime = Column(TIMESTAMP, nullable=True) #added
    wideFormat = Column(Boolean, nullable=True) #added
    fpmmLive = Column(Boolean, nullable=True) #added
    notificationsEnabled = Column(Boolean, nullable=True) #added
    sentDiscord = Column(Boolean, nullable=True) #added
    secondsDelay = Column(Integer, nullable=True) #added
    readyForCron = Column(Boolean, nullable=True) #added
    fee = Column(Float, nullable=True) #added
    clobTokenIds = relationship("ClobTokenId", back_populates="market")

class ClobTokenId(Base):
    __tablename__ = "clob_token_ids"

    tokenId = Column(String, primary_key=True, index=True)
    marketId = Column(Integer, ForeignKey('markets.id'))
    outcome = Column(String, nullable=True)
    lastTradeFetchTimestamp = Column(TIMESTAMP, nullable=True)
    lastFillFetchTimestamp = Column(TIMESTAMP, nullable=True)
    market = relationship("Market", back_populates="clobTokenIds")

class Participant(Base):
    __tablename__ = "participants"

    address = Column(String, primary_key=True, index=True)
    trades = relationship("Trade", back_populates="participant", foreign_keys='Trade.taker') #Added foreign_keys

    
class Trade(Base):
    __tablename__ = "trades"

    id = Column(String, primary_key=True, index=True)
    transactionHash = Column(String)
    timestamp = Column(TIMESTAMP)
    orderHash = Column(String)
    maker = Column(String, ForeignKey('participants.address'))
    taker = Column(String, ForeignKey('participants.address'))
    makerAssetId = Column(String, ForeignKey('clob_token_ids.tokenId'), nullable=True)
    takerAssetId = Column(String, ForeignKey('clob_token_ids.tokenId'), nullable=True)
    makerAmountFilled = Column(Float)
    takerAmountFilled = Column(Float)
    fee = Column(Float)
    participant = relationship("Participant", back_populates="trades", foreign_keys='Trade.taker') #Added foreign_keys

class Fill(Base):
    __tablename__ = "fills"

    id = Column(String, primary_key=True, index=True)
    timestamp = Column(TIMESTAMP)
    makerAssetId = Column(String, ForeignKey('clob_token_ids.tokenId'), nullable=True)
    takerAssetId = Column(String, ForeignKey('clob_token_ids.tokenId'), nullable=True)
    makerAmountFilled = Column(Float)
    takerAmountFilled = Column(Float)

def fmt_field(k,v):
    is_date = lambda x: (x.endswith("Date") or x.endswith("DateIso") or x.endswith("Timestamp") or x.endswith("At") or x.endswith("Time"))
    is_unix_timestamp = lambda k,v: k.lower().endswith("timestamp") and v.isdigit()
    if is_date(k):
        return isoparse(v.replace('Z', '+00:00'))
    if is_unix_timestamp(k,v):
        return TIMESTAMP.fromtimestamp(int(v))
    if isinstance(v, str) and v == '':
        return None
    if (k == 'makerAssetId' or k == 'takerAssetId') and v == "0":
        return None