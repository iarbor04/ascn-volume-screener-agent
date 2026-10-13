# Install or update from the public GitHub repo (no GitHub integration needed)

The repo is public, so the workspace downloads `dist/package-bundle.json` directly over HTTPS; every file is written byte for byte and checked against its sha256. The user's data in `files/screener/` is never touched. Use this when the workspace has no GitHub integration; otherwise `install-or-update-from-github.md` works the same.

## Prompt

```
Install or update the volume screener package from the public repo iarbor04/ascn-volume-screener-agent (branch main).
Follow the steps exactly. Never retype, shorten or summarize file contents yourself: package files are written only by the script in step 1.

1. If python3 is missing, install it (apk add python3). Then run this shell command exactly as written and show its output:
python3 - <<'PY'
import json,os,base64,hashlib,urllib.request,time
u='https://raw.githubusercontent.com/iarbor04/ascn-volume-screener-agent/main/dist/package-bundle.json?nocache='+str(int(time.time()))
b=json.loads(urllib.request.urlopen(urllib.request.Request(u,headers={'User-Agent':'ascn-install'}),timeout=120).read().decode())
bad=[]
for p,x in b['files'].items():
    d=base64.b64decode(x['b64'])
    if hashlib.sha256(d).hexdigest()!=x['sha256']: bad.append(p); continue
    t='/data/workspace/'+p; os.makedirs(os.path.dirname(t),exist_ok=True); open(t,'wb').write(d)
print(json.dumps({'version':b['version'],'written':len(b['files'])-len(bad),'bad':bad}))
PY
   If it fails or "bad" is not empty, stop and report.
2. Run python3 files/scripts/package.py apply-addons, then python3 files/scripts/package.py init. Show both outputs.
3. Do not add, update or remove skills with skills_manage: skills are the files skills/<name>/SKILL.md written in step 1.
4. Run python3 -m py_compile files/scripts/screener.py files/scripts/package.py && echo ok and check it prints ok.
5. Run python3 files/scripts/package.py tidy, then python3 files/scripts/package.py check. Report "clean" and, if false, the modified, missing, extra_files and extra_skills lists.
6. Report each step in one line: done, skipped or failed and why. Send nothing more.
```
