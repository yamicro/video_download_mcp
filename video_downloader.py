import yt_dlp, asyncio, logging, sys
from pathlib import Path
from mcp.server.fastmcp import FastMCP

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s | %(levelname)s | %(message)s",
    stream=sys.stderr
)
log = logging.getLogger("video-dl")

app = FastMCP("any-video-downloader")

@app.tool()
def list_cookies() -> list[str]:
    """列出可用 Cookie 文件名（位于 ./cookies/ 目录）"""
    return [p.name for p in Path("cookies").glob("*.cookies")]

@app.tool()
async def download_video(
    url: str,
    cookiefile: str | None = None,
    outdir: str = "./downloads"
) -> dict:
    Path(outdir).mkdir(parents=True, exist_ok=True)
    cookiefile = "bilibili.cookie"
    prefer = "bv+ba/best[height<=1080]" if "bilibili.com" in url else "bestvideo*+bestaudio/best"
    log.debug(f"首选格式：{prefer}")
    r = await _try(url, outdir, prefer, cookiefile)
    if r["status"] == "ok" or "Requested format" not in r["reason"]:
        return r

    # fallback
    opts = {"quiet": True}
    if cookiefile:
        opts["cookiefile"] = cookiefile
    log.debug("第一次失败，开始 probe 可用格式…")
    formats = yt_dlp.YoutubeDL(opts).extract_info(url, download=False)["formats"]
    for f in formats:
        if f.get("vcodec") != "none" and f.get("acodec") != "none":
            log.debug(f"回退到 format_id={f['format_id']}")
            return await _try(url, outdir, f["format_id"], cookiefile)

    return {"status": "error", "reason": "no combined video+audio format"}


async def _try(url, outdir, fmt, cookiefile):
    ydl_opts = {
        "format": fmt,
        "outtmpl": str(Path(outdir) / "%(title)s-%(id)s.%(ext)s"),
        "merge_output_format": "mp4",
        "progress_hooks": [_hook],
        "logger": log,
    }
    if cookiefile:
        ydl_opts["cookiefile"] = cookiefile

    log.info(f"▶ 开始下载：{url}  format={fmt}")
    try:
        await asyncio.get_running_loop().run_in_executor(
            None, lambda: yt_dlp.YoutubeDL(ydl_opts).download([url])
        )
        log.info("✅ 下载完成")
        return {"status": "ok", "path": ydl_opts["outtmpl"]}
    except yt_dlp.DownloadError as e:
        log.error("❌ DownloadError: %s", e)
        return {"status": "error", "reason": str(e)}


def _hook(d):
    if d["status"] == "downloading":
        pct = d.get("_percent_str", "").strip()
        log.debug(f"… {pct} {d.get('filename','')}")
    elif d["status"] == "finished":
        log.debug("🎬 正在合并流…")


if __name__ == "__main__":
    log.info("🚀 any-video-downloader ready")
    app.run(transport="stdio")
