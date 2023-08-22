from pydantic import BaseModel
from typing import Optional, List, Dict, Union
from enum import Enum
import json


class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Enum):
            return obj.value
        return super().default(obj)


def pydantic_to_mongo(obj) -> dict:
    obj_json = json.dumps(obj.dict(), cls=CustomJSONEncoder)
    return json.loads(obj_json)


def restrict(cls, obj):
    return cls(**obj.dict())


class UserLevel(Enum):
    GUEST = 0
    USER = 1
    ADMIN = 2


class JobType(Enum):
    TRAIN = 0
    TEST = 1
    WATCH = 2


class JobStatus(Enum):
    PENDING = 0
    RUN = 1
    STOP = 2


class JobCancelType(Enum):
    STOP = "STOP"
    KILL = "KILL"


class ItemRequestScope(Enum):
    USER = "user"
    ALL = "all"


class ItemType(Enum):
    AGENTS = "Agents"
    GAMES = "Games"


class UserLogin(BaseModel):
    name: str
    pwd: str


class SimpleUserRequest(BaseModel):
    userName: str


class ItemListRequest(SimpleUserRequest):
    scope: ItemRequestScope


class UserCore(BaseModel):
    name: str = ""
    level: UserLevel = UserLevel.USER
    sound: bool = True
    soundLevel: float = 1.0
    animate: bool = True
    animationSpeed: int = 6
    legends: bool = True
    paletteName: str = "One"
    agents: list[str] = []


class User(UserCore):
    pwd: str = ""
    logs: list[str] = []
    lastLog: int = 0


class UserLoginResponse(BaseModel):
    status: str
    content: Optional[User]


class UserUpdateSettings(BaseModel):
    name: str
    sound: bool
    soundLevel: float
    animate: bool
    animationSpeed: int
    legends: bool
    paletteName: str


class AgentCore(BaseModel):
    user: str
    name: str
    N: int
    alpha: float
    decay: float
    step: int
    minAlpha: float


class AgentDescription(AgentCore):
    bestScore: int
    maxTile: int
    lastTrainingEpisode: int
    history: List[float]
    collectStep: int


class Agent(AgentDescription):
    weightSignature: List[int]
    initialAlpha: float


class BaseJob(BaseModel):
    description: Optional[str]
    type: Optional[JobType]
    status: Optional[JobStatus]
    start: Optional[int]
    timeElapsed: Optional[int]
    remainingTimeEstimate: Optional[int]


class TrainingAgentJob(AgentCore, BaseJob):
    episodes: int
    isNew: bool


class WatchAgentJobBase(BaseJob):
    user: str
    name: str
    depth: int
    width: int
    trigger: int


class TestAgentJob(WatchAgentJobBase):
    episodes: int


Job: type = Union[TrainingAgentJob, TestAgentJob, None]


class JobDescriptionBase(BaseModel):
    type: JobType
    description: str
    name: str
    episodes: int
    start: str
    timeElapsed: str
    remainingTimeEstimate: str


class TrainJobDescription(JobDescriptionBase):
    currentAlpha: float


class TestJobDescription(JobDescriptionBase):
    depth: int
    width: int
    trigger: int


JobDescription = Union[TrainJobDescription, TestJobDescription, None]


class JobUpdateResponse(BaseModel):
    status: str
    job: Optional[JobDescription]


class JobCancelRequest(BaseModel):
    description: str
    type: JobCancelType


# Logs
class LogsUpdateResponse(BaseModel):
    status: str
    logs: Optional[list[str]]


class AgentListResponse(BaseModel):
    status: str
    list: Optional[Dict[str, AgentDescription]]


class JustNamesResponse(BaseModel):
    status: str
    list: Optional[List[str]]


# Games
class GameCore(BaseModel):
    user: str
    name: str
    row: List[List[int]]
    score: int


class GameWatch(BaseModel):
    name: str
    initial: List[List[int]]
    score: int
    numMoves: int


class Offset(BaseModel):
    x: int
    y: int


class GameTile(BaseModel):
    position: Offset
    value: int


class GameDescription(GameCore):
    numMoves: int
    maxTile: int


class Game(GameCore):
    initial: List[List[int]]
    moves: List[int]
    tiles: List[GameTile]


class GameListResponse(BaseModel):
    status: str
    list: Optional[Dict[str, GameDescription]]


class FullGameResponse(BaseModel):
    status: str
    game: Optional[Game]


class WatchAgentJob(WatchAgentJobBase):
    startGame: GameWatch
    previous: str
    newGame: Optional[bool]
    loadingWeights: Optional[bool]


class GameWatchNew(BaseModel):
    user: str
    startGame: GameWatch


class NewMovesRequest(SimpleUserRequest):
    name: str
    numMoves: int


class NewMovesResponse(BaseModel):
    moves: List[int]
    tiles: List[GameTile]
    loadingWeights: bool


# Delete item
class ItemDeleteRequest(BaseModel):
    name: str
    kind: ItemType
