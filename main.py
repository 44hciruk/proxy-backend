import json
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from ssh_setup import SSHSetup

app = FastAPI(title="VPS Proxy Setup API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class SetupRequest(BaseModel):
    ip: str
    root_password: str
    proxy_user: str = "squid_test"
    proxy_password: str = "password"
    proxy_port: int = 50000
    ssh_port: int = 22
    provider: str = "webarena"
    os_type: str = "almalinux"


def sse(step: str, status: str, **extra) -> str:
    payload = {"step": step, "status": status, **extra}
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def run_setup(req: SetupRequest):
    ssh = SSHSetup()

    # SSH接続
    yield sse("SSH接続中...", "running")
    try:
        ssh.connect(req.ip, req.ssh_port, "root", req.root_password)
        yield sse("SSH接続成功", "ok")
    except Exception as e:
        yield sse(f"SSH接続失敗: {e}", "error")
        return

    try:
        # OS別セットアップ実行
        for step_msg, step_status in ssh.get_steps(
            req.os_type, req.proxy_user, req.proxy_password, req.proxy_port
        ):
            yield sse(step_msg, step_status)

        # SSH切断
        ssh.close()

        # 完了
        compact = f"{req.ip}:{req.proxy_port}:{req.proxy_user}:{req.proxy_password}"
        yield sse("完了", "done", proxy=compact)

    except Exception as e:
        yield sse(f"エラー: {e}", "error")
    finally:
        ssh.close()


@app.post("/setup")
async def setup(req: SetupRequest):
    return StreamingResponse(
        run_setup(req),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/health")
async def health():
    return {"status": "ok"}
