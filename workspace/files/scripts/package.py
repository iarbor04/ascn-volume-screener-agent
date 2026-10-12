#!/usr/bin/env python3
"""Package integrity for an ASCN marketplace agent. Standard library only.

The workspace has two parts:
- the package: IDENTITY.md, SOUL.md, the AGENTS addon, skills/, knowledge/, defaults/, files/scripts/.
  It comes from GitHub and only package updates change it;
- the data folder (for example files/smm/): everything the agent creates or learns while working (profiles,
  config, posts, models, emails, reports, backups). It is excluded when the agent is published to the marketplace,
  and every new user starts it fresh from defaults/.

  python3 files/scripts/package.py start   the marketplace start prompt runs this: init, then print only the text the
                                           agent sends the user ("SAY: ..."; "THEN: ..." = what to do next); always begins
                                           onboarding, archiving data that came with a marketplace copy
  python3 files/scripts/package.py intro <language>   the second message, in the chosen language: what the agent can do
  python3 files/scripts/package.py init    create missing data files from defaults/ (never overwrites; for JSON
                                           files adds new keys only) and move files from older package layouts
  python3 files/scripts/package.py check   before publishing: are the package files intact, and what else in the
                                           workspace would ship to clients
  python3 files/scripts/package.py reset   start the data folder over, as a new user gets it (run only when the owner
                                           asks, e.g. before a test run); the old contents move to <data>/_archive/
  python3 files/scripts/package.py prepublish   run in the workspace you publish from, right before publishing: reset,
                                           then tidy, so a copy never gets this workspace's data even if the
                                           marketplace does not exclude the data folder
  python3 files/scripts/package.py tidy    before publishing: move stray files that would ship to clients (tool dumps,
                                           leftovers of interrupted installs) into <data>/_moved/; nothing is deleted
  python3 files/scripts/package.py unpack  install the package from the newest saved GitHub result for
                                           dist/package-bundle.json (files/tool-output/), byte for byte, hash-checked
  python3 files/scripts/package.py apply-addons   rewrite the package blocks in AGENTS.md / AUTOMATIONS.md (top blocks first in the file)
  python3 files/scripts/package.py verify <path> ...   does each file match its hash in package.json
  python3 files/scripts/package.py repair  fix files that differ from the package only by the final newline
  python3 files/scripts/package.py skill <name>   record that a package skill is being used, then read its SKILL.md;
                                           the log is <data>/_usage/skills.jsonl
  python3 files/scripts/package.py activity [--since <time>]   read-only: skills used and files created or changed
                                           since <time> (epoch seconds, ISO time, or 30m / 2h / 1d; default 1d)

Reads files/scripts/package.json, generated from git by tools/build_manifest.py in the agent's repo.
"""
import hashlib
import json
import os
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = Path(os.environ.get("PACKAGE_ROOT") or HERE.parents[1])  # /data/workspace
IGNORED_DIRS = {"__pycache__", ".git"}
LANGUAGES = ["🇬🇧 English", "🇷🇺 Русский", "🇪🇸 Español", "🇧🇷 Português", "🇩🇪 Deutsch", "🇫🇷 Français", "🇮🇹 Italiano",
             "🇹🇷 Türkçe", "🇸🇦 العربية", "🇨🇳 中文"]


def manifest():
    return json.loads((HERE / "package.json").read_text(encoding="utf-8"))


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def rel(p):
    return p.relative_to(ROOT).as_posix()


def _size(f):
    try:
        return f.stat().st_size
    except OSError:  # a file removed while we were looking, or a broken link
        return 0


def _is_file(f):
    try:
        return f.is_file()
    except OSError:
        return False


def merge_missing(dst, src):
    """Adds keys from src that dst lacks, recursively. Never changes an existing value."""
    added = []
    for k, v in src.items():
        if k not in dst:
            dst[k] = v
            added.append(k)
        elif isinstance(v, dict) and isinstance(dst[k], dict):
            added += [f"{k}.{x}" for x in merge_missing(dst[k], v)]
    return added


def init():
    m = manifest()
    data = ROOT / m["data_root"]
    first_run = not data.exists()
    moved, conflicts, created, merged = [], [], [], []
    for old, new in (m.get("legacy") or {}).items():
        src, dst = ROOT / old, data / new
        if not src.exists():
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.is_dir():
            dst.mkdir(parents=True, exist_ok=True)
            for f in sorted(src.rglob("*")):
                target = dst / f.relative_to(src)
                if f.is_file() and not target.exists():
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(f), str(target))
            if not any(f.is_file() for f in src.rglob("*")):
                shutil.rmtree(src)
                moved.append(f"{old} -> {rel(dst)}")
            else:
                conflicts.append(old)
        elif not dst.exists():
            shutil.move(str(src), str(dst))
            moved.append(f"{old} -> {rel(dst)}")
        else:
            conflicts.append(old)
    defaults = ROOT / m.get("defaults", "defaults")
    refresh = set(m.get("refresh") or [])
    for f in sorted(defaults.rglob("*")) if defaults.exists() else []:
        if not f.is_file():
            continue
        r = f.relative_to(defaults).as_posix()
        target = data / r
        if r in refresh and target.exists() and sha256(target) != sha256(f):
            shutil.copyfile(f, target)  # package documentation kept in the data folder: always the latest version
            created.append(rel(target) + " (refreshed)")
        elif not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(f, target)
            created.append(rel(target))
        elif f.suffix == ".json":
            try:
                cur = json.loads(target.read_text(encoding="utf-8"))
                new = json.loads(f.read_text(encoding="utf-8"))
            except (ValueError, OSError):
                continue
            if isinstance(cur, dict) and isinstance(new, dict):
                added = merge_missing(cur, new)
                if added:
                    target.write_text(json.dumps(cur, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                    merged.append({"file": rel(target), "added_keys": added})
    out = {"ok": not conflicts, "first_run": first_run, "data_root": m["data_root"], "created": created, "moved": moved,
           "merged": merged, "conflicts": conflicts}
    if conflicts:
        out["hint"] = "an old file and its new copy both exist; keep the one with the user's data and delete the other"
    return out


def reset():
    """Start the data folder over as a new user would get it. Nothing is deleted: the current contents move to
    <data folder>/_archive/<UTC time>/, which stays inside the excluded data folder."""
    from datetime import datetime, timezone
    m = manifest()
    data = ROOT / m["data_root"]
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    archived = []
    if data.exists():
        dest = data / "_archive" / stamp
        for item in sorted(data.iterdir()):
            if item.name == "_archive":
                continue
            dest.mkdir(parents=True, exist_ok=True)
            shutil.move(str(item), str(dest / item.name))
            archived.append(item.name)
    out = init()
    out["archived_to"] = f"{m['data_root']}/_archive/{stamp}" if archived else None
    out["archived"] = archived
    return out


def _set_up(m):
    """Has onboarding filled the user's main profile? True when it differs from the package default."""
    profile = (m.get("start") or {}).get("profile")
    if not profile:
        return False
    cur, default = ROOT / m["data_root"] / profile, ROOT / m.get("defaults", "defaults") / profile
    return cur.is_file() and (not default.is_file() or sha256(cur) != sha256(default))


def start():
    """The marketplace start prompt runs this once, when a user hires the agent: it always begins onboarding.
    Data already in the data folder came with the marketplace copy, not from this user, so it moves to the archive
    first. Prints the first message (hello and a language choice) after "SAY:", then a "THEN:" line."""
    m = manifest()
    s = m.get("start") or {}
    failed = s.get("failed") or "Setup is not finished."
    try:
        out = reset() if _set_up(m) else init()
    except Exception as e:  # noqa: BLE001 - any setup error becomes one plain line for the user
        return ["SAY:", f"{failed} ({type(e).__name__})"]
    if out["conflicts"]:
        return ["SAY:", failed]
    hello = s["greeting"].splitlines()[0]
    choice = [f"{i}. {lang}" for i, lang in enumerate(LANGUAGES, 1)]
    then = ("THEN: when the user picks a language (a number, a language name, or a message in any language), run "
            "python3 files/scripts/package.py intro <the number or the language name> and send the text after SAY: "
            "exactly as printed (translate it first only if the output says TRANSLATE), and nothing else; ")
    then += f"then follow skill {s['skill']} with the user's next message." if s.get("skill") else \
        "then treat the user's next message as the start of onboarding."
    return ["SAY:", hello, "", "**Choose your language / Выбери язык:**", "", *choice, "", "Or just write in your language.", then]


LANGUAGE_CODES = {"1": "en", "english": "en", "2": "ru", "русский": "ru", "russian": "ru", "3": "es", "4": "pt",
                  "5": "de", "6": "fr", "7": "it", "8": "tr", "9": "ar", "10": "zh"}


def _chat_markdown(text):
    """The chat renders markdown, where a single line break joins lines into one paragraph. Every line except
    numbered list items becomes its own paragraph, and short labels that end with a colon become bold headings."""
    import re
    out = []
    for line in text.strip().splitlines():
        line = line.rstrip()
        if not line:
            continue
        numbered = re.match(r"\d+\.\s", line)
        if out and not (numbered and re.match(r"\d+\.\s", out[-1])):
            out.append("")
        heading = line.endswith(":") and not numbered and len(line.split()) <= 5  # short labels only, not sentences
        out.append(f"**{line}**" if heading else line)
    return "\n".join(out)


def intro(language=""):
    """The second message, after the user picks a language: what the agent can do and what to send to start.
    Prints the package's own translation when there is one; otherwise the English text with a request to translate."""
    s = manifest().get("start") or {}
    key = language.strip().lower().strip(".")
    code = LANGUAGE_CODES.get(key, key)
    ready = (s.get("greeting_by_language") or {}).get(code) or (s.get("greeting") if code == "en" else None)
    text = ready or s.get("greeting", "")
    body = "\n".join(text.splitlines()[1:]).strip()  # the hello line was already in the first message
    if ready:
        return "SAY:\n" + _chat_markdown(body)
    named = LANGUAGES[int(key) - 1].split(" ", 1)[1] if key.isdigit() and 0 < int(key) <= len(LANGUAGES) else language
    target = named or "the user's language"
    return (f"TRANSLATE into {target}, keeping the line breaks, blank lines, bold and emojis, then SAY:\n"
            + _chat_markdown(body))


def prepublish():
    """Before publishing: the data folder starts over (old contents archived) and stray files are tidied away."""
    r = reset()
    t = tidy()
    return {"archived_to": r.get("archived_to"), "tidied": t["moved"], "clean_now": t["clean_now"],
            "data_is_fresh": not _set_up(manifest())}


def _stray_skill_dirs(m):
    """Folders in skills/ that are not package skills and are not real skills (no SKILL.md or an invalid name)."""
    root = ROOT / "skills"
    if not root.is_dir():
        return []
    out = []
    for d in root.iterdir():
        if d.is_dir() and d.name not in m["skills"]:
            valid = all(ch.isalnum() or ch == "-" for ch in d.name) and (d / "SKILL.md").is_file()
            if not valid:
                out.append(d)
    return out


def tidy():
    """Moves files that would ship to clients but are not part of the package into the excluded data folder."""
    from datetime import datetime, timezone
    m = manifest()
    first = init()  # old-layout files go to their proper place in the data folder first
    report = check()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dest = ROOT / m["data_root"] / "_moved" / stamp
    moved = []
    for r in report["extra_files"]:
        src = ROOT / r
        if src.is_file() and not r.startswith("skills/"):
            target = dest / r
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(target))
            moved.append(r)
    for d in _stray_skill_dirs(m):
        target = dest / rel(d)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(d), str(target))
        moved.append(rel(d) + "/")
    left = check()
    return {"init": {k: first[k] for k in ("created", "moved", "conflicts")}, "moved_to": rel(dest) if moved else None,
            "moved": moved, "clean_now": left["clean"],
            "still_to_review": {k: left[k] for k in ("modified", "missing", "extra_skills", "extra_files", "legacy_left")}}


def _load_bundle():
    """The newest saved GitHub result for dist/package-bundle.json. The platform saves large tool results either as
    files/tool-output/*.json ({"result": "..."}) or as files/apps_*.txt (plain text)."""
    files = list((ROOT / "files" / "tool-output").glob("*.json")) + list((ROOT / "files").glob("apps_*.txt"))
    files += list((ROOT / "files").glob("*/_moved/*/files/apps_*.txt"))
    for f in sorted(files, key=lambda x: x.stat().st_mtime, reverse=True):
        try:
            raw = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        try:
            doc = json.loads(raw)
            r = doc.get("result", raw) if isinstance(doc, dict) else raw
        except ValueError:
            r = raw
        if not isinstance(r, str):
            continue
        i = r.find("Retrieved file dist/package-bundle.json")
        if i == -1:
            continue
        try:
            meta = json.loads(r[i:].split("\n", 1)[1])
            return json.loads(meta["content"]), rel(f)
        except (ValueError, KeyError, IndexError):
            continue
    return None, None


def unpack():
    import base64
    bundle, src = _load_bundle()
    if not bundle:
        return {"ok": False, "error": "no saved GitHub result for dist/package-bundle.json in files/tool-output/; fetch it first"}
    written, bad = [], []
    for path, x in sorted(bundle["files"].items()):
        data = base64.b64decode(x["b64"])
        if hashlib.sha256(data).hexdigest() != x["sha256"]:
            bad.append(path)
            continue
        target = ROOT / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        written.append(path)
    return {"ok": not bad, "version": bundle.get("version"), "source": src, "written": len(written), "bad": bad}


def apply_addons():
    m = manifest()
    out = []
    for a in m.get("addons") or []:
        into, src = ROOT / a["into"], ROOT / a["file"]
        body = src.read_text(encoding="utf-8")
        text = into.read_text(encoding="utf-8") if into.is_file() else ""
        i = text.find(a["marker"])
        if a.get("position") == "top":
            rest = text
            if i != -1:
                j = text.find(a["end"], i)
                rest = text[:i] + (text[j + len(a["end"]):] if j != -1 else text[i + len(a["marker"]):])
            new = body.rstrip("\n") + "\n\n" + rest.lstrip("\n")
        else:
            head = text[:i] if i != -1 else text
            new = head.rstrip("\n") + ("\n\n" if head.strip() else "") + body
        into.write_text(new, encoding="utf-8")
        out.append({"into": a["into"], "replaced": i != -1, "marker_count": new.count(a["marker"])})
    return {"ok": all(x["marker_count"] == 1 for x in out), "addons": out}


def verify(paths):
    files = manifest()["files"]
    res = {}
    for p in paths:
        f = ROOT / p
        res[p] = {"match": f.is_file() and p in files and sha256(f) == files[p], "expected_in_package": p in files,
                  "size": f.stat().st_size if f.is_file() else None}
    return {"ok": all(v["match"] for v in res.values()), "files": res}


def repair():
    files = manifest()["files"]
    fixed = []
    for p, digest in files.items():
        f = ROOT / p
        if not f.is_file() or sha256(f) == digest:
            continue
        b = f.read_bytes()
        for cand in (b + b"\n", b.rstrip(b"\n") + b"\n", b.replace(b"\r\n", b"\n"), b.replace(b"\r\n", b"\n") + b"\n"):
            if hashlib.sha256(cand).hexdigest() == digest:
                f.write_bytes(cand)
                fixed.append(p)
                break
    left = check()
    return {"fixed": fixed, "still_modified": left["modified"], "missing": left["missing"]}


def _now():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc)


def _iso(t):
    from datetime import datetime, timezone
    return datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def skill(name):
    """Records that a package skill is being used, so the owner (and evals) can see which skills do the work.
    The log lives in the excluded data folder; logging never blocks the skill."""
    m = manifest()
    name = (name or "").strip().strip("/")
    f = ROOT / "skills" / name / "SKILL.md"
    if not name or not all(ch.isalnum() or ch == "-" for ch in name) or not f.is_file():
        return {"ok": False, "error": f"no skill {name!r}", "skills": sorted(m.get("skills") or [])}
    now = _now()
    rec = {"ts": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "t": round(now.timestamp(), 1), "skill": name, "version": m.get("version")}
    try:
        log = ROOT / m["data_root"] / "_usage" / "skills.jsonl"
        log.parent.mkdir(parents=True, exist_ok=True)
        with open(log, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except OSError:
        pass
    return {"ok": True, "skill": name, "next": f"read skills/{name}/SKILL.md with file_read and follow it"}


def _since(arg):
    import re
    from datetime import datetime
    now = _now().timestamp()
    if not arg:
        return now - 86400
    h = re.fullmatch(r"(\d+(?:\.\d+)?)([smhd])", arg.strip())
    if h:
        return now - float(h.group(1)) * {"s": 1, "m": 60, "h": 3600, "d": 86400}[h.group(2)]
    try:
        return float(arg)
    except ValueError:
        return datetime.fromisoformat(arg.strip().replace("Z", "+00:00")).timestamp()


def activity(since_arg=None, limit=300):
    """What the agent did since a moment: skills it recorded and files created or changed anywhere in the workspace,
    each tagged data (excluded on publish), package, platform, or other (would ship to clients). Read-only."""
    m = manifest()
    t0 = _since(since_arg)
    skills = []
    log = ROOT / m["data_root"] / "_usage" / "skills.jsonl"
    if log.is_file():
        for line in log.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            if isinstance(rec, dict) and (rec.get("t") or 0) >= t0:
                skills.append({k: rec.get(k) for k in ("t", "skill")})
    files, data_prefix = [], m["data_root"].rstrip("/") + "/"
    for f in ROOT.rglob("*"):
        r = rel(f)
        if any(part in IGNORED_DIRS for part in r.split("/")) or "/_archive/" in r or "/_usage/" in r or not _is_file(f):
            continue
        try:
            st = f.stat()
        except OSError:
            continue
        if st.st_mtime < t0:
            continue
        kind = "data" if r.startswith(data_prefix) else "package" if r in m["files"] or r == "files/scripts/package.json" \
            else "platform" if _skip(r, m) else "other"
        files.append({"t": round(st.st_mtime, 1), "path": r, "size": st.st_size, "kind": kind})
    files.sort(key=lambda x: x["t"])
    now = _now().timestamp()
    return {"since": _iso(t0), "now": _iso(now), "now_t": round(now, 2), "skills": skills, "files": files[:limit], "files_total": len(files)}


def _skip(path_rel, m):
    """Paths that never ship from the package side: the data folder (excluded on publish), platform files, caches."""
    if any(part in IGNORED_DIRS for part in path_rel.split("/")):
        return True
    for p in m.get("platform") or []:
        if path_rel == p.rstrip("/") or (p.endswith("/") and path_rel.startswith(p)):
            return True
    return path_rel.startswith(m["data_root"].rstrip("/") + "/")


def check():
    m = manifest()
    files = m["files"]
    missing, modified = [], []
    for path, digest in sorted(files.items()):
        p = ROOT / path
        if not p.is_file():
            missing.append(path)
        elif sha256(p) != digest:
            modified.append(path)
    extra_skills = sorted(d.name for d in (ROOT / "skills").iterdir()
                          if d.is_dir() and d.name not in m["skills"]) if (ROOT / "skills").is_dir() else []
    extra_files = []
    for p in sorted(ROOT.rglob("*")):
        if not _is_file(p):
            continue
        r = rel(p)
        if r in files or r == "files/scripts/package.json" or _skip(r, m):
            continue
        extra_files.append(r)
    addons = []
    for a in m.get("addons") or []:
        into, src = ROOT / a["into"], ROOT / a["file"]
        text = into.read_text(encoding="utf-8") if into.is_file() else ""
        body = src.read_text(encoding="utf-8").strip() if src.is_file() else ""
        count = text.count(a["marker"])
        addons.append({"into": a["into"], "marker_count": count, "matches_package": bool(body) and body in text,
                       "ok": count == 1 and bool(body) and body in text})
    legacy = [old for old in (m.get("legacy") or {}) if (ROOT / old).exists()]
    data = ROOT / m["data_root"]
    data_files = [f for f in data.rglob("*") if _is_file(f)] if data.exists() else []
    user_md = ROOT / "USER.md"
    user = None
    if user_md.is_file():
        lines = user_md.read_text(encoding="utf-8", errors="replace").splitlines()
        user = {"lines": len(lines), "head": [line[:160] for line in lines[:15]]}
    platform = []
    for p in m.get("platform") or []:
        target = ROOT / p.rstrip("/")
        found = [target] if target.is_file() else sorted(f for f in target.rglob("*") if f.is_file()) if target.is_dir() else []
        for f in found:
            platform.append({"path": rel(f), "lines": len(f.read_text(encoding="utf-8", errors="replace").splitlines())})
    clean = not (missing or modified or extra_skills or extra_files or legacy) and all(a["ok"] for a in addons)
    return {
        "clean": clean,
        "package": {"agent": m["agent"], "version": m["version"], "files": len(files)},
        "modified": modified, "missing": missing,
        "extra_skills": extra_skills,
        "extra_files": extra_files[:200], "extra_files_total": len(extra_files),
        "addons": addons, "legacy_left": legacy,
        "data_folder": {"path": m["data_root"], "files": len(data_files),
                        "bytes": sum(_size(f) for f in data_files), "excluded_on_publish": True},
        "user_md": user,
        "platform_files": platform,
        "publish_exclude": m.get("publish_exclude") or [],
        "how_to_fix": {
            "modified or missing": "reinstall the package from GitHub (marketplace/install-or-update-from-github.md)",
            "extra_files / extra_skills": "they would ship to every client: move them into the data folder or delete them",
            "user_md": "USER.md describes the workspace owner; make sure it holds nothing about you before publishing",
        },
    }


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    cmds = {"init": init, "check": check, "reset": reset, "prepublish": prepublish, "tidy": tidy, "unpack": unpack,
            "apply-addons": apply_addons, "repair": repair}
    if cmd == "start":
        print("\n".join(start()))
        return
    if cmd == "intro":
        print(intro(" ".join(sys.argv[2:])))
        return
    if cmd == "verify" and len(sys.argv) > 2:
        print(json.dumps(verify(sys.argv[2:]), ensure_ascii=False, indent=2))
        return
    if cmd == "skill" and len(sys.argv) > 2:
        out = skill(sys.argv[2])
        print(json.dumps(out, ensure_ascii=False))
        sys.exit(0 if out["ok"] else 1)
    if cmd == "activity":
        since = sys.argv[sys.argv.index("--since") + 1] if "--since" in sys.argv[:-1] else None
        print(json.dumps(activity(since), ensure_ascii=False, separators=(",", ":")))
        return
    if cmd not in cmds:
        sys.exit(__doc__)
    print(json.dumps(cmds[cmd](), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
