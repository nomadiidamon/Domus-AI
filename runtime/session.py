# Handles session management commands and tracking of active sessions

from dataclasses import dataclass
from datetime import datetime


_sessions = {}


@dataclass
class Session:

    name: str
    process: object
    session_type: str
    metadata: dict
    started_at: datetime

    def is_running(self):
        return self.process.poll() is None


def remove_session(name):

    if name in _sessions:
        del _sessions[name]


def get_session(name):

    return _sessions.get(name)


def create_session(
    name,
    process,
    session_type,
    metadata=None
):

    session = Session(
        name=name,
        process=process,
        session_type=session_type,
        metadata=metadata or {},
        started_at=datetime.now()
    )


    _sessions[name] = session

    return session

def get_status():

    status = []

    for name, session in _sessions.items():

        status.append(
            {
                "name": name,
                "type": session.session_type,
                "running": session.is_running(),
                "pid": session.process.pid,
                "started": session.started_at
            }
        )

    return status

def stop_session(name):

    session = get_session(name)

    if not session:
        return False


    session.process.terminate()

    remove_session(name)

    return True

def get_session(pid):
    # Logic to retrieve a session by its process ID
    pass