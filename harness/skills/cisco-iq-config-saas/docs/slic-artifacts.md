# Download SLIC Artifacts (dev / nprd / prod)

Use this read-only procedure to obtain the current Config/Security Hardening
SLIC artifacts — also referred to as the rules and ICs (Implementation
Checks) — for local use. It does not use Secrets Manager or an APISIX
tunnel.

## Per-env config (USW2)

```text
              dev                                nprd                               prod
Profile:      platform-dev-admin                 platform-nprd-admin                platform-prod-admin
Region:       us-west-2                          us-west-2                          us-west-2
S3 bucket:    cx-usw2-dev01-vc-s3-assessments-configuration   cx-usw2-nprd01-vc-s3-assessments-configuration   cx-usw2-prod01-vc-s3-assessments-configuration
Local store:  slic-ic-packages/local_store.json  (rules, same key, all envs)
IC BOM:       slic-ic-packages/ic_bom.json        (IC bill-of-materials, same key, all envs)
```

The bucket per env is configured in
`cbp-engine/helm/cluster-values/<env>/usw2-eks01/values.yaml`. The object keys
come from the cbp-engine Helm defaults. Only USW2 is confirmed for this
bucket today; other regions are unverified.

## Download

Use the wrapper script, which resolves each current object version before
downloading so both requests are pinned to the objects inspected at the start
of the operation:

```bash
bash "$SKILL_DIR/scripts/download_slic_artifacts.sh" dev  ./out/dev
bash "$SKILL_DIR/scripts/download_slic_artifacts.sh" nprd ./out/nprd
bash "$SKILL_DIR/scripts/download_slic_artifacts.sh" prod ./out/prod
```

Dest dir is a required argument — the script never picks a destination for
you. Pass a path outside any repo, or confirm it's gitignored if it isn't.

If an AWS command fails with an expired-token or SSO credential error, run
`duo-sso` once and retry the failed command. Do not switch profiles.

## Verify

Validate JSON and print non-sensitive checksums:

```bash
DEST="./out/prod"   # whichever dest-dir you passed to the download script
export DEST

python3 - <<'PY'
import hashlib
import json
import os
from pathlib import Path

root = Path(os.environ["DEST"])
for path in (root / "local_store.json", root / "ic_bom.json"):
    data = path.read_bytes()
    json.loads(data)
    print(path.name, len(data), hashlib.sha256(data).hexdigest())
PY
```

## Safety

- All three envs are accessed read-only here: use `head-object` and
  `get-object` only, never `put-object`/`delete-object`.
- Pass a dest-dir outside all repositories, or, if it's inside one, confirm
  it's gitignored before downloading.
- Do not overwrite tracked `data/local_store.json` or `data/ic_bom.json`.
- Do not commit downloaded artifacts; IC implementations may be sensitive.
- Do not print artifact contents into chat or logs.
- Record object version IDs and SHA-256 hashes alongside whatever the
  artifacts are used for, so the exact objects can be traced back later.
