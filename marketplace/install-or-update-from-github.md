# Install or update from GitHub

One prompt for a first install and for every update. Files are never retyped by the model: the repo carries `dist/package-bundle.json` (every package file in base64 with its sha256, built by `tools/build_manifest.py`), the agent fetches it with one GitHub integration call, the platform saves the large result in `files/tool-output/`, and a script writes the files byte for byte and checks every hash. The user's data in `files/screener/` is never touched.

Measured on 2026-09-30 with the other ASCN agents: when the agent copied files one by one through the integration, it replaced skills with placeholders or short summaries and still reported success. Use only this prompt.

## Prompt

```
Install or update the volume screener package from GitHub. Repo: iarbor04/ascn-volume-screener-agent, branch main.
Follow the steps exactly. Never retype, shorten or summarize file contents yourself: package files are written only by the script in step 2.

1. Call the GitHub integration action github-get-repository-content with repository iarbor04/ascn-volume-screener-agent, path dist/package-bundle.json, ref main. The result is large and the platform saves it to a file (files/tool-output/ or files/apps_*.txt). Do not copy its content anywhere.
2. Run this shell command exactly as written and show its output:
python3 - <<'PY'
import json,glob,os,base64,hashlib
b=None
for f in sorted(glob.glob('/data/workspace/files/tool-output/*.json')+glob.glob('/data/workspace/files/apps_*.txt'),key=os.path.getmtime,reverse=True):
    raw=open(f,encoding='utf-8',errors='replace').read()
    try: r=json.loads(raw).get('result',raw)
    except Exception: r=raw
    i=r.find('Retrieved file dist/package-bundle.json') if isinstance(r,str) else -1
    if i==-1: continue
    b=json.loads(json.loads(r[i:].split(chr(10),1)[1])['content']); break
if not b: raise SystemExit('bundle not found: repeat step 1')
bad=[]
for p,x in b['files'].items():
    d=base64.b64decode(x['b64'])
    if hashlib.sha256(d).hexdigest()!=x['sha256']: bad.append(p); continue
    t='/data/workspace/'+p; os.makedirs(os.path.dirname(t),exist_ok=True); open(t,'wb').write(d)
print(json.dumps({'version':b['version'],'written':len(b['files'])-len(bad),'bad':bad}))
PY
   If the bundle is not found or "bad" is not empty, stop and report.
3. Run python3 files/scripts/package.py apply-addons (it rewrites the package block in AGENTS.md), then python3 files/scripts/package.py init (it creates missing files in files/screener/ from defaults/ and adds new settings keys without changing existing values). Show both outputs.
4. Skills are used from the files skills/<name>/SKILL.md, which step 2 wrote. Do not add, update or remove skills with skills_manage: it rewrites the files from a retyped copy.
5. If python3 is missing, install it (apk add python3). Run python3 -m py_compile files/scripts/screener.py files/scripts/package.py && echo ok and check it prints ok.
6. Run python3 files/scripts/package.py tidy, then python3 files/scripts/package.py check. Report "clean" and, if it is false, the modified, missing, extra_files and extra_skills lists.
7. Report each step in one line: done, skipped or failed and why.
8. If python3 files/scripts/screener.py context shows "profile_filled": false, run python3 files/scripts/package.py intro ru and send the text after SAY: exactly as printed. Otherwise send nothing more.
```
